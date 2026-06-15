import logging
from datetime import datetime
from typing import Optional

from kb_server.auth.models import (
    AuditLog,
    ErasureRequest,
    ErasureStatus,
    User,
)

log = logging.getLogger("kb-mcp.auth.erasure")


class ErasureManager:
    def __init__(self, session):
        self._session = session

    def request_erasure(
        self, user_id: str, requested_by: str, reason: Optional[str] = None
    ) -> ErasureRequest:
        user = self._session.query(User).filter(User.id == user_id).first()
        if user is None:
            raise ValueError(f"User not found: {user_id}")

        er = ErasureRequest(
            user_id=user_id,
            status="erasure_requested",
            requested_by=requested_by,
            reason=reason,
        )
        self._session.add(er)

        user.erasure_status = ErasureStatus.erasure_requested
        user.erasure_requested_at = datetime.utcnow()
        self._session.flush()

        entry = AuditLog(
            actor_id=requested_by,
            action="user.erasure_requested",
            resource_type="user",
            resource_id=user_id,
        )
        self._session.add(entry)
        self._session.commit()
        log.info("Erasure requested for user: %s", user_id)
        return er

    def approve_erasure(self, request_id: str, approved_by: str) -> bool:
        er = (
            self._session.query(ErasureRequest)
            .filter(ErasureRequest.id == request_id)
            .first()
        )
        if er is None:
            return False
        if er.status != "erasure_requested":
            return False

        er.status = "erasure_approved"
        er.approved_by = approved_by
        er.resolved_at = datetime.utcnow()

        user = self._session.query(User).filter(User.id == er.user_id).first()
        if user:
            user.erasure_status = ErasureStatus.erasure_approved
            user.erasure_approved_at = datetime.utcnow()
        self._session.flush()

        entry = AuditLog(
            actor_id=approved_by,
            action="user.erasure_approved",
            resource_type="user",
            resource_id=er.user_id,
        )
        self._session.add(entry)
        self._session.commit()
        log.info("Erasure approved: %s", request_id)
        return True

    def execute_erasure(self, request_id: str) -> bool:
        er = (
            self._session.query(ErasureRequest)
            .filter(ErasureRequest.id == request_id)
            .first()
        )
        if er is None:
            return False
        if er.status != "erasure_approved":
            return False

        user = self._session.query(User).filter(User.id == er.user_id).first()
        if user is None:
            return False

        short_id = user.id[:8]
        user.username = f"deleted-user-{short_id}"
        user.is_active = False
        user.erasure_status = ErasureStatus.erasure_completed
        user.erasure_completed_at = datetime.utcnow()

        for key in user.api_keys:
            self._session.delete(key)

        er.status = "erasure_completed"
        er.resolved_at = datetime.utcnow()
        self._session.flush()

        entry = AuditLog(
            actor_id=er.approved_by,
            action="user.erasure_completed",
            resource_type="user",
            resource_id=er.user_id,
        )
        self._session.add(entry)
        self._session.commit()
        log.info("Erasure executed for user: %s", er.user_id)
        return True

    def get_erasure_request(self, request_id: str) -> Optional[ErasureRequest]:
        return (
            self._session.query(ErasureRequest)
            .filter(ErasureRequest.id == request_id)
            .first()
        )

    def get_user_erasure_requests(self, user_id: str) -> list[ErasureRequest]:
        return (
            self._session.query(ErasureRequest)
            .filter(ErasureRequest.user_id == user_id)
            .order_by(ErasureRequest.created_at.desc())
            .all()
        )

    def export_user_data(self, user_id: str) -> Optional[dict]:
        user = self._session.query(User).filter(User.id == user_id).first()
        if user is None:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": (
                user.created_at.isoformat() if user.created_at else None
            ),
            "api_keys": [
                {
                    "id": k.id,
                    "prefix": k.prefix,
                    "description": k.description,
                    "is_revoked": k.is_revoked,
                    "created_at": (
                        k.created_at.isoformat() if k.created_at else None
                    ),
                }
                for k in user.api_keys
            ],
        }
