import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import delete as sa_delete

from kb_server.auth.models import (
    ApiKey,
    AuditLog,
    ErasureStatus,
    User,
    create_session,
)

log = logging.getLogger("kb-mcp.auth.service")


class AuthService:
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._session = create_session(db_path)

    @property
    def session(self):
        """Expose the SQLAlchemy session for shared use by ErasureManager."""
        return self._session

    # ── User CRUD ────────────────────────────────────────────────

    def create_user(self, username: str, role: str = "user") -> User:
        existing = (
            self._session.query(User).filter(User.username == username).first()
        )
        if existing:
            raise ValueError(f"User already exists: {username}")

        user = User(username=username, role=role)
        self._session.add(user)
        self._session.flush()

        self._write_audit_log(
            actor_id=user.id,
            action="user.created",
            resource_type="user",
            resource_id=user.id,
        )
        self._session.commit()
        log.info("Created user: %s (role=%s)", username, role)
        return user

    def list_users(self) -> list[User]:
        return (
            self._session.query(User)
            .filter(User.erasure_status != ErasureStatus.erasure_completed)
            .order_by(User.created_at.desc())
            .all()
        )

    def get_user(self, user_id: str) -> Optional[User]:
        return self._session.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        return (
            self._session.query(User).filter(User.username == username).first()
        )

    def delete_user(self, user_id: str) -> bool:
        user = self.get_user(user_id)
        if user is None:
            return False
        short_id = user.id[:8]
        user.username = f"deleted-user-{short_id}"
        user.is_active = False
        for key in user.api_keys:
            self._session.delete(key)
        self._session.flush()
        self._write_audit_log(
            actor_id=user_id,
            action="user.deleted",
            resource_type="user",
            resource_id=user_id,
        )
        self._session.commit()
        log.info("Deleted user: %s", user_id)
        return True

    # ── API Key Management ───────────────────────────────────────

    def create_api_key(
        self, user_id: str, description: str = ""
    ) -> tuple[str, ApiKey]:
        user = self.get_user(user_id)
        if user is None:
            raise ValueError(f"User not found: {user_id}")

        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:8]

        api_key = ApiKey(
            user_id=user_id,
            key_hash=key_hash,
            prefix=prefix,
            description=description,
        )
        self._session.add(api_key)
        self._session.flush()

        self._write_audit_log(
            actor_id=user_id,
            action="api_key.created",
            resource_type="api_key",
            resource_id=api_key.id,
        )
        self._session.commit()
        log.info("Created API key for user: %s", user_id)
        return raw_key, api_key

    def list_api_keys(self, user_id: str) -> list[ApiKey]:
        return (
            self._session.query(ApiKey)
            .filter(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
            .all()
        )

    def revoke_api_key(self, key_id: str) -> bool:
        key = self._session.query(ApiKey).filter(ApiKey.id == key_id).first()
        if key is None:
            return False
        key.is_revoked = True
        self._session.flush()
        self._write_audit_log(
            actor_id=key.user_id,
            action="api_key.revoked",
            resource_type="api_key",
            resource_id=key_id,
        )
        self._session.commit()
        log.info("Revoked API key: %s", key_id)
        return True

    def record_key_usage(self, raw_key: str) -> None:
        """Record last_used_at for a key (called on explicit auth, not every verify)."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = (
            self._session.query(ApiKey)
            .filter(ApiKey.key_hash == key_hash)
            .first()
        )
        if api_key:
            api_key.last_used_at = datetime.now(timezone.utc).replace(
                tzinfo=None
            )
            self._session.commit()

    def verify_key(self, raw_key: str) -> Optional[User]:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = (
            self._session.query(ApiKey)
            .filter(
                ApiKey.key_hash == key_hash,
                ApiKey.is_revoked == False,  # noqa: E712
            )
            .first()
        )
        if api_key is None:
            return None

        user = self.get_user(api_key.user_id)
        if user is None:
            return None
        if not user.is_active:
            return None
        if user.erasure_status == ErasureStatus.erasure_completed:
            return None

        self._session.commit()
        return user

    # ── Audit Logging ────────────────────────────────────────────

    def _write_audit_log(
        self,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )
        self._session.add(entry)

    def prune_audit_logs(self, days: int = 90) -> int:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            days=days
        )
        result = self._session.execute(
            sa_delete(AuditLog).where(AuditLog.timestamp < cutoff)
        )
        self._session.commit()
        log.info(
            "Pruned %d audit log entries older than %d days",
            result.rowcount,
            days,
        )
        return result.rowcount

    def get_audit_logs(
        self,
        actor_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        query = self._session.query(AuditLog).order_by(
            AuditLog.timestamp.desc()
        )
        if actor_id:
            query = query.filter(AuditLog.actor_id == actor_id)
        return query.limit(limit).all()
