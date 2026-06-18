import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


class ErasureStatus(str, Enum):
    active = "active"
    erasure_requested = "erasure_requested"
    erasure_approved = "erasure_approved"
    erasure_completed = "erasure_completed"
    erasure_rejected = "erasure_rejected"


class User(Base):  # type: ignore[valid-type,misc]
    __tablename__ = "users"

    id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=True)
    role = Column(String(20), nullable=False, default="user")
    is_active = Column(Boolean, default=True)
    erasure_status = Column(String(30), nullable=False, default="active")
    erasure_requested_at = Column(DateTime, nullable=True)
    erasure_approved_at = Column(DateTime, nullable=True)
    erasure_completed_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    api_keys = relationship(
        "ApiKey", back_populates="user", cascade="all, delete-orphan"
    )
    erasure_requests = relationship(
        "ErasureRequest",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class ApiKey(Base):  # type: ignore[valid-type,misc]
    __tablename__ = "api_keys"

    id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_hash = Column(String(64), unique=True, nullable=False)
    prefix = Column(String(8), nullable=False)
    description = Column(String(255), default="")
    is_revoked = Column(Boolean, default=False)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    user = relationship("User", back_populates="api_keys")


class AuditLog(Base):  # type: ignore[valid-type,misc]
    __tablename__ = "audit_logs"

    id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    timestamp = Column(
        DateTime,
        nullable=False,
        index=True,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    actor_id = Column(String(36), index=True, nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)


class ErasureRequest(Base):  # type: ignore[valid-type,misc]
    __tablename__ = "erasure_requests"

    id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(30), nullable=False, default="erasure_requested")
    requested_by = Column(String(36), nullable=True)
    approved_by = Column(String(36), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    resolved_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="erasure_requests")


class UserSession(Base):  # type: ignore[valid-type,misc]
    __tablename__ = "user_sessions"

    id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_token = Column(String(64), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    last_used_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    is_revoked = Column(Boolean, default=False)

    user = relationship("User")


def create_session(db_path: Path):
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
