import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, cast

from sqlalchemy import delete as sa_delete

from kb_server.auth.models import (
    ApiKey,
    AuditLog,
    ErasureStatus,
    User,
    UserSession,
    create_session,
)

log = logging.getLogger("kb-mcp.auth.service")


class AuthService:
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._session = create_session(db_path)
        self._run_migrations()

    def _run_migrations(self) -> None:
        """Apply schema migrations for existing databases."""
        from sqlalchemy import inspect as sa_inspect, text as sa_text
        inspector = sa_inspect(self._session.bind)
        columns = [c["name"] for c in inspector.get_columns("users")]
        if "password_hash" not in columns:
            self._session.execute(
                sa_text(
                    "ALTER TABLE users ADD COLUMN "
                    "password_hash VARCHAR(128)"
                )
            )
            self._session.commit()
            log.info("Added password_hash column to users table")

    @property
    def session(self):
        """Expose the SQLAlchemy session for shared use by ErasureManager."""
        return self._session

    # ── Password Management ──────────────────────────────────────

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password using PBKDF2-SHA256 with a random salt."""
        salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 100_000
        )
        return f"{salt}:{dk.hex()}"

    @staticmethod
    def _check_password(password: str, stored: str) -> bool:
        """Verify a password against its PBKDF2-SHA256 hash."""
        try:
            salt, hash_hex = stored.split(":", 1)
            dk = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt.encode(), 100_000
            )
            return hmac.compare_digest(dk.hex(), hash_hex)
        except (ValueError, AttributeError):
            return False

    def set_password(self, user_id: str, password: str) -> None:
        """Set a user's password hash."""
        user = self.get_user(user_id)
        if user is None:
            raise ValueError(f"User not found: {user_id}")
        user.password_hash = self._hash_password(password)
        self._session.commit()
        log.info("Password set for user: %s", user_id)

    def verify_login(
        self, username: str, password: str
    ) -> Optional[User]:
        """Verify username/password credentials and return the User on success."""
        user = self.get_user_by_username(username)
        if user is None:
            return None
        if not user.is_active:
            return None
        if user.erasure_status == ErasureStatus.erasure_completed:
            return None
        if not user.password_hash:
            return None
        if not self._check_password(password, user.password_hash):
            return None
        return user

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
            actor_id=cast(str, user.id),
            action="user.created",
            resource_type="user",
            resource_id=cast(str, user.id),
        )
        self._session.commit()
        log.info("Created user: %s (role=%s)", username, role)
        return user

    def list_users(self) -> list[User]:
        return (  # type: ignore[no-any-return]
            self._session.query(User)
            .filter(User.erasure_status != ErasureStatus.erasure_completed)
            .order_by(User.created_at.desc())
            .all()
        )

    def get_user(self, user_id: str) -> Optional[User]:
        return self._session.query(User).filter(User.id == user_id).first()  # type: ignore[no-any-return]

    def get_user_by_username(self, username: str) -> Optional[User]:
        return (  # type: ignore[no-any-return]
            self._session.query(User).filter(User.username == username).first()
        )

    def delete_user(self, user_id: str) -> bool:
        user = self.get_user(user_id)
        if user is None:
            return False
        short_id = user.id[:8]
        user.username = f"deleted-user-{short_id}"  # type: ignore[assignment]
        user.is_active = False  # type: ignore[assignment]
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
            resource_id=cast(str, api_key.id),
        )
        self._session.commit()
        log.info("Created API key for user: %s", user_id)
        return raw_key, api_key

    def list_api_keys(self, user_id: str) -> list[ApiKey]:
        return (  # type: ignore[no-any-return]
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
            actor_id=cast(str, key.user_id),
            action="api_key.revoked",
            resource_type="api_key",
            resource_id=key_id,
        )
        self._session.commit()
        log.info("Revoked API key: %s", key_id)
        return True

    def record_key_usage(self, raw_key: str) -> None:
        """Record last_used_at for a key (called on explicit auth)."""
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

    # ── Admin Account Seeding ─────────────────────────────────────

    def _ensure_admin_password(self, user_id: str) -> None:
        """Set or reset the default admin password."""
        user = self.get_user(user_id)
        if user is None:
            return
        if not user.password_hash:
            self.set_password(user_id, "admin")
            log.info("Set default password for admin user")

    def ensure_admin_account(self) -> Optional[str]:
        """Ensure an admin user exists with an active API key.

        Returns:
            The raw API key if a new one was created, or None if
            the admin already has an active key.
        """
        admin_user = self.get_user_by_username("admin")
        if admin_user is None:
            admin_user = self.create_user(username="admin", role="admin")
            self.set_password(cast(str, admin_user.id), "admin")
            raw_key, _ = self.create_api_key(
                cast(str, admin_user.id),
                description="Default admin key for UI login",
            )
            log.info("=" * 60)
            log.info("DEFAULT ADMIN ACCOUNT READY")
            log.info("  Username: admin")
            log.info("  Password: admin")
            log.info("  API Key: %s", raw_key)
            log.info("=" * 60)
            print("=" * 60, flush=True)
            print("DEFAULT ADMIN ACCOUNT READY", flush=True)
            print("  Username: admin", flush=True)
            print("  Password: admin", flush=True)
            print(f"  API Key: {raw_key}", flush=True)
            print("=" * 60, flush=True)
            return raw_key

        self._ensure_admin_password(cast(str, admin_user.id))

        active_keys = [
            k for k in admin_user.api_keys if not k.is_revoked
        ]
        if not active_keys:
            raw_key, _ = self.create_api_key(
                cast(str, admin_user.id),
                description="Default admin key for UI login",
            )
            log.info("=" * 60)
            log.info("DEFAULT ADMIN ACCOUNT READY")
            log.info("  Username: admin")
            log.info("  Password: admin")
            log.info("  API Key: %s", raw_key)
            log.info("=" * 60)
            print("=" * 60, flush=True)
            print("DEFAULT ADMIN ACCOUNT READY", flush=True)
            print("  Username: admin", flush=True)
            print("  Password: admin", flush=True)
            print(f"  API Key: {raw_key}", flush=True)
            print("=" * 60, flush=True)
            return raw_key

        return None

    # ── Session Management ───────────────────────────────────────

    def create_session_record(
        self,
        user_id: str,
        session_token: str,
        ip_address: str = "unknown",
        user_agent: str = "unknown",
    ) -> None:
        session = UserSession(
            user_id=user_id,
            session_token=session_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(session)
        self._session.commit()

    def get_user_session(
        self, user_id: str, session_token: str
    ) -> Optional[UserSession]:
        return self._session.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.session_token == session_token,
            UserSession.is_revoked == False,  # noqa: E712
        ).first()  # type: ignore[no-any-return]

    def list_user_sessions(
        self, user_id: str
    ) -> list[UserSession]:
        return self._session.query(UserSession).filter(
            UserSession.user_id == user_id,
        ).order_by(
            UserSession.last_used_at.desc()
        ).all()  # type: ignore[no-any-return]

    def revoke_session(self, session_id: str, user_id: str) -> bool:
        session = self._session.query(UserSession).filter(
            UserSession.id == session_id,
        ).first()
        if session is None:
            return False
        session.is_revoked = True
        self._session.commit()
        log.info("Revoked session: %s (user: %s)", session_id, user_id)
        return True

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
        return result.rowcount  # type: ignore[no-any-return]

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
        return query.limit(limit).all()  # type: ignore[no-any-return]
