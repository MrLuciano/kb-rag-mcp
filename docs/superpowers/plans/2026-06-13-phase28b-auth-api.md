# Phase 28b: Auth & User Management API

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Full REST API for user management, API key CRUD, role-based access control, and GDPR erasure workflow.

**Architecture:** New `kb_server/auth/` package with SQLAlchemy models, FastAPI dependency guards, and REST router. Builds on existing `AuthRegistry` (SQLite) — the REST API becomes the primary interface; CLI remains backward-compatible by calling the same service layer. GDPR erasure uses a state machine with tombstone pattern.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, `secrets.token_urlsafe`, SHA-256, PyJWT.

---

### Task 1: SQLAlchemy models for User, ApiKey, AuditLog, ErasureRequest

**Files:**
- Create: `kb_server/auth/__init__.py`
- Create: `kb_server/auth/models.py`
- Test: `tests/test_auth_api.py`

- [ ] **Step 1: Write the failing test — models create and persist**

`tests/test_auth_api.py`:
```python
import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def auth_db():
    db_path = Path(tempfile.mktemp(suffix=".db"))
    from kb_server.auth.models import create_tables, User, ApiKey, AuditLog, \
        ErasureRequest
    engine = create_tables(db_path)
    yield engine, db_path
    db_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_create_user(auth_db):
    engine, _ = auth_db
    from kb_server.auth.models import User
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    async with AsyncSession(engine) as session:
        user = User(username="testuser", role="admin")
        session.add(user)
        await session.commit()
        result = await session.execute(select(User).where(User.username == "testuser"))
        fetched = result.scalar_one()
        assert fetched.username == "testuser"
        assert fetched.role == "admin"
        assert fetched.is_active is True
        assert fetched.id is not None


@pytest.mark.asyncio
async def test_create_api_key(auth_db):
    engine, _ = auth_db
    from kb_server.auth.models import User, ApiKey
    import hashlib
    from sqlalchemy.ext.asyncio import AsyncSession
    async with AsyncSession(engine) as session:
        user = User(username="keyuser", role="user")
        session.add(user)
        await session.flush()
        raw = "test-raw-key-12345"
        key = ApiKey(
            user_id=user.id,
            key_hash=hashlib.sha256(raw.encode()).hexdigest(),
            prefix=raw[:8],
            description="test key",
        )
        session.add(key)
        await session.commit()
        assert key.id is not None
        assert key.prefix == "test-raw"


@pytest.mark.asyncio
async def test_user_cascade_delete(auth_db):
    engine, _ = auth_db
    from kb_server.auth.models import User, ApiKey
    import hashlib
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    async with AsyncSession(engine) as session:
        user = User(username="cascadeuser", role="user")
        session.add(user)
        await session.flush()
        key = ApiKey(
            user_id=user.id,
            key_hash=hashlib.sha256(b"x").hexdigest(),
            prefix="xxxxxxxx",
        )
        session.add(key)
        await session.commit()
        await session.delete(user)
        await session.commit()
        keys = await session.execute(
            select(ApiKey).where(ApiKey.user_id == user.id)
        )
        assert keys.scalars().all() == []
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_create_user -x -v 2>&1 | tail -10`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create models**

`kb_server/auth/__init__.py`:
```python
```

`kb_server/auth/models.py`:
```python
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Text, Enum,
    create_engine, event,
)
from sqlalchemy.dialects.sqlite import UUID as SQLiteUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class ErasureStatus(str, enum.Enum):
    active = "active"
    erasure_requested = "erasure_requested"
    erasure_approved = "erasure_approved"
    erasure_completed = "erasure_completed"
    erasure_rejected = "erasure_rejected"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                     default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="user")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
                                                  onupdate=datetime.utcnow)
    erasure_status: Mapped[str] = mapped_column(String(32),
                                                 default=ErasureStatus.active.value)
    erasure_requested_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    erasure_approved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    erasure_completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    erasure_requests = relationship("ErasureRequest", back_populates="user",
                                     cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                     default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                          nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")
    is_revoked: Mapped[bool] = mapped_column(default=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="api_keys")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                     default=lambda: str(uuid.uuid4()))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
                                                 index=True)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    details: Mapped[Optional[str]] = mapped_column(nullable=True)


class ErasureRequest(Base):
    __tablename__ = "erasure_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                     default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                          nullable=False)
    status: Mapped[str] = mapped_column(String(32),
                                         default=ErasureStatus.erasure_requested.value)
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    user = relationship("User", back_populates="erasure_requests")


def create_tables(db_path: Path):
    db_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(db_url, echo=False)

    async def init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    import asyncio
    asyncio.run(init())
    return engine
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_create_user -x -v 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kb_server/auth/ tests/test_auth_api.py
git commit -m "feat(28b): add auth models (User, ApiKey, AuditLog, ErasureRequest)"
```

---

### Task 2: Auth service layer (CRUD)

**Files:**
- Create: `kb_server/auth/service.py`
- Modify: `tests/test_auth_api.py`

- [ ] **Step 1: Write the failing test — auth service CRUD**

Append to `tests/test_auth_api.py`:
```python
@pytest.mark.asyncio
async def test_auth_service_create_user(auth_db):
    engine, _ = auth_db
    from kb_server.auth.service import AuthService
    svc = AuthService(engine)
    user = await svc.create_user("alice", "admin")
    assert user.username == "alice"
    assert user.role == "admin"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_auth_service_create_api_key(auth_db):
    engine, _ = auth_db
    from kb_server.auth.service import AuthService
    svc = AuthService(engine)
    user = await svc.create_user("bob", "user")
    raw_key, key_obj = await svc.create_api_key(user.id, "my key")
    assert len(raw_key) > 20
    assert key_obj.prefix == raw_key[:8]
    assert key_obj.is_revoked is False


@pytest.mark.asyncio
async def test_auth_service_verify_key(auth_db):
    engine, _ = auth_db
    from kb_server.auth.service import AuthService
    svc = AuthService(engine)
    user = await svc.create_user("charlie", "user")
    raw_key, _ = await svc.create_api_key(user.id)
    verified = await svc.verify_key(raw_key)
    assert verified is not None
    assert verified.username == "charlie"


@pytest.mark.asyncio
async def test_auth_service_list_keys(auth_db):
    engine, _ = auth_db
    from kb_server.auth.service import AuthService
    svc = AuthService(engine)
    user = await svc.create_user("dave", "user")
    await svc.create_api_key(user.id, "key1")
    await svc.create_api_key(user.id, "key2")
    keys = await svc.list_api_keys(user.id)
    assert len(keys) == 2


@pytest.mark.asyncio
async def test_auth_service_revoke_key(auth_db):
    engine, _ = auth_db
    from kb_server.auth.service import AuthService
    svc = AuthService(engine)
    user = await svc.create_user("eve", "user")
    _, key_obj = await svc.create_api_key(user.id)
    await svc.revoke_api_key(key_obj.id)
    keys = await svc.list_api_keys(user.id)
    assert keys[0].is_revoked is True


@pytest.mark.asyncio
async def test_auth_service_list_users(auth_db):
    engine, _ = auth_db
    from kb_server.auth.service import AuthService
    svc = AuthService(engine)
    await svc.create_user("u1", "admin")
    await svc.create_user("u2", "user")
    users = await svc.list_users()
    assert len(users) >= 2
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_auth_service_create_user -x -v 2>&1 | tail -10`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create auth service**

`kb_server/auth/service.py`:
```python
import secrets
import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from kb_server.auth.models import User, ApiKey, AuditLog


class AuthService:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def create_user(self, username: str, role: str = "user") -> User:
        async with AsyncSession(self.engine) as session:
            user = User(username=username, role=role)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            # audit
            session.add(AuditLog(
                actor_id=user.id, action="user.created",
                resource_type="user", resource_id=user.id,
            ))
            await session.commit()
            return user

    async def list_users(self) -> list[User]:
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(User).where(User.erasure_status != "erasure_completed")
                .order_by(User.created_at.desc())
            )
            return list(result.scalars().all())

    async def get_user(self, user_id: str) -> Optional[User]:
        async with AsyncSession(self.engine) as session:
            return await session.get(User, user_id)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()

    async def create_api_key(self, user_id: str, description: str = ""
                             ) -> tuple[str, ApiKey]:
        raw = secrets.token_urlsafe(32)
        prefix = raw[:8]
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        async with AsyncSession(self.engine) as session:
            key = ApiKey(
                user_id=user_id, key_hash=key_hash,
                prefix=prefix, description=description,
            )
            session.add(key)
            session.add(AuditLog(
                actor_id=user_id, action="api_key.created",
                resource_type="api_key",
            ))
            await session.commit()
            await session.refresh(key)
            return raw, key

    async def list_api_keys(self, user_id: str) -> list[ApiKey]:
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(ApiKey).where(
                    ApiKey.user_id == user_id,
                ).order_by(ApiKey.created_at.desc())
            )
            return list(result.scalars().all())

    async def revoke_api_key(self, key_id: str) -> bool:
        async with AsyncSession(self.engine) as session:
            key = await session.get(ApiKey, key_id)
            if key and not key.is_revoked:
                key.is_revoked = True
                session.add(AuditLog(
                    actor_id=key.user_id, action="api_key.revoked",
                    resource_type="api_key", resource_id=key_id,
                ))
                await session.commit()
                return True
            return False

    async def verify_key(self, raw_key: str) -> Optional[User]:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(ApiKey).where(
                    ApiKey.key_hash == key_hash,
                    ApiKey.is_revoked == False,
                )
            )
            key = result.scalar_one_or_none()
            if key is None:
                return None
            key.last_used_at = datetime.utcnow()
            user = await session.get(User, key.user_id)
            if user and not user.is_active:
                return None
            if user and user.erasure_status == "erasure_completed":
                return None
            await session.commit()
            return user
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_auth_service_create_user -x -v 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kb_server/auth/service.py tests/test_auth_api.py
git commit -m "feat(28b): add auth service layer with CRUD"
```

---

### Task 3: FastAPI dependencies (guards)

**Files:**
- Create: `kb_server/auth/deps.py`
- Modify: `tests/test_auth_api.py`

- [ ] **Step 1: Write the failing test — dependency guards**

Append to `tests/test_auth_api.py`:
```python
@pytest.mark.asyncio
async def test_deps_get_current_user(auth_db):
    engine, _ = auth_db
    from kb_server.auth.service import AuthService
    from kb_server.auth.deps import get_current_user
    svc = AuthService(engine)
    user = await svc.create_user("guarduser", "user")
    raw, _ = await svc.create_api_key(user.id)

    class MockRequest:
        headers = {"x-api-key": raw}
        app = type("obj", (object,), {"state": type("st", (object,),
                    {"auth_engine": engine})})()

    result = await get_current_user(request=MockRequest())
    assert result is not None
    assert result.username == "guarduser"


@pytest.mark.asyncio
async def test_deps_require_admin_allows_admin(auth_db):
    engine, _ = auth_db
    from kb_server.auth.service import AuthService
    from kb_server.auth.deps import require_admin
    svc = AuthService(engine)
    user = await svc.create_user("adminuser", "admin")
    from unittest.mock import AsyncMock
    result = await require_admin(current_user=user)
    assert result.username == "adminuser"


@pytest.mark.asyncio
async def test_deps_require_admin_rejects_user(auth_db):
    engine, _ = auth_db
    from kb_server.auth.service import AuthService
    from kb_server.auth.deps import require_admin
    from fastapi import HTTPException
    svc = AuthService(engine)
    user = await svc.create_user("regular", "user")
    try:
        await require_admin(current_user=user)
        assert False, "Should have raised"
    except HTTPException as e:
        assert e.status_code == 403
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_deps_get_current_user -x -v 2>&1 | tail -10`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create dependency guards**

`kb_server/auth/deps.py`:
```python
from fastapi import HTTPException, Request
from fastapi.security import APIKeyHeader
from typing import Optional

from kb_server.auth.service import AuthService
from kb_server.auth.models import User

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    request: Request,
    api_key: Optional[str] = None,
) -> User:
    if api_key is None:
        header = request.headers.get("x-api-key") or request.headers.get("authorization", "")
        if header.startswith("Bearer "):
            api_key = header[7:]
        else:
            api_key = header
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    engine = getattr(request.app.state, "auth_engine", None)
    if engine is None:
        raise HTTPException(status_code=500, detail="Auth not configured")

    svc = AuthService(engine)
    user = await svc.verify_key(api_key)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return user


async def require_admin(current_user: User = None) -> User:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_auth(current_user: User = None) -> User:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    return current_user
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_deps_get_current_user -x -v 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kb_server/auth/deps.py tests/test_auth_api.py
git commit -m "feat(28b): add FastAPI auth dependency guards"
```

---

### Task 4: REST API router

**Files:**
- Create: `kb_server/auth/router.py`
- Create: `kb_server/auth/schemas.py`
- Modify: `tests/test_auth_api.py`

- [ ] **Step 1: Write the failing test — auth API endpoints**

Append to `tests/test_auth_api.py`:
```python
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI


@pytest.fixture
def auth_app(auth_db):
    engine, _ = auth_db
    app = FastAPI()
    app.state.auth_engine = engine
    from kb_server.auth.router import router
    app.include_router(router)
    return app


@pytest.mark.asyncio
async def test_api_create_user(auth_app):
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/users", json={
            "username": "api_user", "role": "user"
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "api_user"
    assert "id" in data


@pytest.mark.asyncio
async def test_api_list_users(auth_app):
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/v1/users", json={"username": "u1", "role": "user"})
        await ac.post("/api/v1/users", json={"username": "u2", "role": "admin"})
        resp = await ac.get("/api/v1/users")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_api_create_key(auth_app):
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        user_resp = await ac.post("/api/v1/users", json={
            "username": "key_owner", "role": "user"
        })
        uid = user_resp.json()["id"]
        key_resp = await ac.post("/api/v1/api-keys", json={
            "user_id": uid, "description": "test key"
        })
    assert key_resp.status_code == 200
    data = key_resp.json()
    assert "raw_key" in data
    assert len(data["raw_key"]) > 20


@pytest.mark.asyncio
async def test_api_list_keys(auth_app):
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        user_resp = await ac.post("/api/v1/users", json={
            "username": "key_list_owner", "role": "user"
        })
        uid = user_resp.json()["id"]
        await ac.post("/api/v1/api-keys", json={"user_id": uid, "description": "k1"})
        await ac.post("/api/v1/api-keys", json={"user_id": uid, "description": "k2"})
        resp = await ac.get(f"/api/v1/api-keys?user_id={uid}")
    assert resp.status_code == 200
    keys = resp.json()
    assert len(keys) == 2
    for k in keys:
        assert "key_hash" not in k
        assert "prefix" in k
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_api_create_user -x -v 2>&1 | tail -10`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create Pydantic schemas**

`kb_server/auth/schemas.py`:
```python
from pydantic import BaseModel
from typing import Optional


class CreateUserRequest(BaseModel):
    username: str
    role: str = "user"


class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    created_at: str


class CreateApiKeyRequest(BaseModel):
    user_id: str
    description: str = ""


class ApiKeyResponse(BaseModel):
    id: str
    prefix: str
    description: str
    is_revoked: bool
    created_at: str


class ApiKeyCreatedResponse(ApiKeyResponse):
    raw_key: str
```

- [ ] **Step 4: Create auth router**

`kb_server/auth/router.py`:
```python
from fastapi import APIRouter, HTTPException, Depends
from typing import List

from kb_server.auth.schemas import (
    CreateUserRequest, UserResponse, CreateApiKeyRequest,
    ApiKeyResponse, ApiKeyCreatedResponse,
)
from kb_server.auth.service import AuthService
from kb_server.auth.models import User
from kb_server.auth.deps import get_current_user

router = APIRouter(prefix="/api/v1", tags=["auth"])


def _get_svc(request) -> AuthService:
    return AuthService(request.app.state.auth_engine)


@router.post("/users", response_model=UserResponse)
async def create_user(body: CreateUserRequest, request):
    svc = _get_svc(request)
    existing = await svc.get_user_by_username(body.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = await svc.create_user(body.username, body.role)
    return UserResponse(
        id=user.id, username=user.username, role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users(request):
    svc = _get_svc(request)
    users = await svc.list_users()
    return [
        UserResponse(
            id=u.id, username=u.username, role=u.role,
            is_active=u.is_active,
            created_at=u.created_at.isoformat() if u.created_at else "",
        ) for u in users
    ]


@router.get("/users/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id, username=current_user.username,
        role=current_user.role, is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat()
        if current_user.created_at else "",
    )


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, request):
    svc = _get_svc(request)
    user = await svc.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    async with svc.engine.begin() as conn:
        from sqlalchemy import delete as sa_delete
        from kb_server.auth.models import ApiKey, ErasureRequest
        await conn.execute(sa_delete(ApiKey).where(ApiKey.user_id == user_id))
        await conn.execute(
            sa_delete(ErasureRequest).where(ErasureRequest.user_id == user_id)
        )
    await svc.create_user.__wrapped__  # noop
    user.username = f"deleted-user-{user.id[:8]}"
    user.is_active = False
    user.erasure_status = "erasure_completed"
    async with svc.engine.begin() as session:
        from sqlalchemy import update as sa_update
        await session.execute(
            sa_update(User.__table__).where(User.id == user_id).values(
                username=user.username, is_active=False,
                erasure_status="erasure_completed",
            )
        )
    return {"status": "deleted", "user_id": user_id}


@router.post("/api-keys", response_model=ApiKeyCreatedResponse)
async def create_api_key(body: CreateApiKeyRequest, request):
    svc = _get_svc(request)
    user = await svc.get_user(body.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    raw, key = await svc.create_api_key(body.user_id, body.description)
    return ApiKeyCreatedResponse(
        id=key.id, prefix=key.prefix, description=key.description,
        is_revoked=key.is_revoked,
        created_at=key.created_at.isoformat() if key.created_at else "",
        raw_key=raw,
    )


@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(user_id: str, request):
    svc = _get_svc(request)
    keys = await svc.list_api_keys(user_id)
    return [
        ApiKeyResponse(
            id=k.id, prefix=k.prefix, description=k.description,
            is_revoked=k.is_revoked,
            created_at=k.created_at.isoformat() if k.created_at else "",
        ) for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, request):
    svc = _get_svc(request)
    ok = await svc.revoke_api_key(key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Key not found or already revoked")
    return {"status": "revoked", "key_id": key_id}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_api_create_user -x -v 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add kb_server/auth/router.py kb_server/auth/schemas.py tests/test_auth_api.py
git commit -m "feat(28b): add auth REST API router"
```

---

### Task 5: GDPR erasure workflow

**Files:**
- Create: `kb_server/auth/erasure.py`
- Modify: `kb_server/auth/router.py`
- Modify: `tests/test_auth_api.py`

- [ ] **Step 1: Write the failing test — erasure state machine**

Append to `tests/test_auth_api.py`:
```python
@pytest.mark.asyncio
async def test_erasure_request_submit(auth_db):
    engine, _ = auth_db
    from kb_server.auth.service import AuthService
    from kb_server.auth.erasure import ErasureManager
    svc = AuthService(engine)
    user = await svc.create_user("erase_me", "user")
    mgr = ErasureManager(engine)
    req = await mgr.request_erasure(user.id, user.id)
    assert req.status == "erasure_requested"
    from kb_server.auth.models import AuditLog
    async with engine.begin() as conn:
        from sqlalchemy import select
        result = await conn.execute(
            select(AuditLog).where(AuditLog.action == "user.erasure_requested")
        )
        assert len(result.scalars().all()) >= 1


@pytest.mark.asyncio
async def test_erasure_approve_and_execute(auth_db):
    engine, _ = auth_db
    from kb_server.auth.service import AuthService
    from kb_server.auth.erasure import ErasureManager
    svc = AuthService(engine)
    user = await svc.create_user("erase_me2", "user")
    admin = await svc.create_user("dpo", "admin")
    mgr = ErasureManager(engine)
    req = await mgr.request_erasure(user.id, user.id)
    await mgr.approve_erasure(req.id, admin.id)
    completed = await mgr.execute_erasure(req.id)
    assert completed is True
    erased = await svc.get_user(user.id)
    assert erased is None or erased.erasure_status == "erasure_completed"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_erasure_request_submit -x -v 2>&1 | tail -10`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create ErasureManager**

`kb_server/auth/erasure.py`:
```python
from datetime import datetime
from sqlalchemy import select, update as sa_update, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from kb_server.auth.models import (
    ErasureRequest, AuditLog, User, ApiKey, ErasureStatus,
)


class ErasureManager:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def request_erasure(self, user_id: str, requested_by: str,
                              reason: str = "") -> ErasureRequest:
        async with AsyncSession(self.engine) as session:
            req = ErasureRequest(
                user_id=user_id, requested_by=requested_by,
                reason=reason, status=ErasureStatus.erasure_requested.value,
            )
            session.add(req)
            session.add(AuditLog(
                actor_id=requested_by, action="user.erasure_requested",
                resource_type="user", resource_id=user_id,
            ))
            await session.commit()
            await session.refresh(req)
            return req

    async def approve_erasure(self, request_id: str, approved_by: str
                              ) -> bool:
        async with AsyncSession(self.engine) as session:
            req = await session.get(ErasureRequest, request_id)
            if not req or req.status != ErasureStatus.erasure_requested.value:
                return False
            req.status = ErasureStatus.erasure_approved.value
            req.approved_by = approved_by
            req.resolved_at = datetime.utcnow()
            session.add(AuditLog(
                actor_id=approved_by, action="user.erasure_approved",
                resource_type="erasure_request", resource_id=request_id,
            ))
            await session.commit()
            return True

    async def execute_erasure(self, request_id: str) -> bool:
        async with AsyncSession(self.engine) as session:
            req = await session.get(ErasureRequest, request_id)
            if not req or req.status != ErasureStatus.erasure_approved.value:
                return False
            user_id = req.user_id
            # Anonymize user
            await session.execute(
                sa_update(User.__table__).where(User.id == user_id).values(
                    username=f"deleted-user-{user_id[:8]}",
                    is_active=False,
                    erasure_status=ErasureStatus.erasure_completed.value,
                    erasure_completed_at=datetime.utcnow(),
                )
            )
            # Hard-delete API keys
            await session.execute(
                sa_delete(ApiKey).where(ApiKey.user_id == user_id)
            )
            # Update request
            req.status = ErasureStatus.erasure_completed.value
            session.add(AuditLog(
                actor_id=req.approved_by or req.requested_by,
                action="user.erasure_executed",
                resource_type="user", resource_id=user_id,
            ))
            await session.commit()
            return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_erasure_request_submit -x -v 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 5: Add erasure and export endpoints to router**

Add to `kb_server/auth/router.py`:
```python
@router.post("/users/{user_id}/erasure-request")
async def request_erasure(user_id: str, request):
    from kb_server.auth.erasure import ErasureManager
    mgr = ErasureManager(request.app.state.auth_engine)
    req = await mgr.request_erasure(user_id, user_id)
    return {"request_id": req.id, "status": req.status}


@router.post("/admin/erasure-requests/{request_id}/approve")
async def approve_erasure(request_id: str, request):
    from kb_server.auth.erasure import ErasureManager
    mgr = ErasureManager(request.app.state.auth_engine)
    ok = await mgr.approve_erasure(request_id, "system")
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot approve in current state")
    completed = await mgr.execute_erasure(request_id)
    return {"request_id": request_id, "status": "erasure_completed" if completed else "approved"}


@router.get("/users/{user_id}/export")
async def export_user_data(user_id: str, request):
    svc = _get_svc(request)
    user = await svc.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    keys = await svc.list_api_keys(user_id)
    return {
        "username": user.username,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else "",
        "api_keys": [
            {"prefix": k.prefix, "description": k.description,
             "created_at": k.created_at.isoformat() if k.created_at else ""}
            for k in keys
        ],
    }
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py -x -v 2>&1 | tail -20`
Expected: PASS (all tests)

- [ ] **Step 7: Commit**

```bash
git add kb_server/auth/erasure.py kb_server/auth/router.py tests/test_auth_api.py
git commit -m "feat(28b): add GDPR erasure workflow and data export"
```

---

### Task 6: Audit log auto-prune

**Files:**
- Modify: `kb_server/auth/service.py`
- Modify: `tests/test_auth_api.py`

- [ ] **Step 1: Write the failing test — prune old audit logs**

Append to `tests/test_auth_api.py`:
```python
@pytest.mark.asyncio
async def test_audit_prune(auth_db):
    engine, _ = auth_db
    from kb_server.auth.service import AuthService
    from datetime import datetime, timedelta
    svc = AuthService(engine)
    user = await svc.create_user("prune_test", "user")
    async with engine.begin() as conn:
        from sqlalchemy import select
        from kb_server.auth.models import AuditLog
        result = await conn.execute(
            select(AuditLog).where(AuditLog.actor_id == user.id)
        )
        count_before = len(result.scalars().all())
    pruned = await svc.prune_audit_logs(days=0)  # prunes all
    assert pruned > 0
    async with engine.begin() as conn:
        from sqlalchemy import select
        from kb_server.auth.models import AuditLog
        result = await conn.execute(
            select(AuditLog).where(AuditLog.actor_id == user.id)
        )
        count_after = len(result.scalars().all())
    assert count_after < count_before
```

Add `prune_audit_logs` method to `AuthService` in `kb_server/auth/service.py`:
```python
    async def prune_audit_logs(self, days: int = 90) -> int:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                sa_delete(AuditLog).where(AuditLog.timestamp < cutoff)
            )
            await session.commit()
            return result.rowcount
```

Add import: `from sqlalchemy import delete as sa_delete` at the top.

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_audit_prune -x -v 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add kb_server/auth/service.py tests/test_auth_api.py
git commit -m "feat(28b): add audit log auto-prune (90 day retention)"
```

---

### Task 7: GDPR data inventory document

**Files:**
- Create: `docs/DATA_INVENTORY.md`

- [ ] **Step 1: Create data inventory doc**

`docs/DATA_INVENTORY.md`:
```markdown
# Data Inventory — kb-rag-mcp

**Last updated:** 2026-06-13

| Data Store | Data Categories | PII? | Retention | Deletion Method |
|---|---|---|---|---|
| `users` table (SQLite) | username, role, timestamps | Pseudonymous | Indefinite (active) → tombstone on erasure | Tombstone: anonymize username, clear active status |
| `api_keys` table (SQLite) | key_hash (SHA-256), prefix, timestamps | None | Until user erasure | Hard DELETE on erasure |
| `audit_logs` table (SQLite) | actor_id (UUID), action, timestamp | None | 90 days, auto-prune | HARD DELETE after TTL |
| `config` table (SQLite) | key, value, type, group | None | Indefinite | Direct DELETE |
| Application logs (stdout/files) | Request paths, response codes | None (IP stripped) | 30 days | Log rotation |
| Qdrant vector store | Document chunks, metadata | None (product docs only) | Indefinite | Collection drop |

**Breach notification:** Check `data_inventory.md` to identify affected stores within 72-hour window.
```

- [ ] **Step 2: Commit**

```bash
git add docs/DATA_INVENTORY.md
git commit -m "docs: add GDPR data inventory"
```
