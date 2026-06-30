---
phase: 28b-auth-api
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - kb_server/auth/__init__.py
  - kb_server/auth/models.py
  - kb_server/auth/service.py
  - kb_server/auth/deps.py
  - kb_server/auth/router.py
  - kb_server/auth/schemas.py
  - kb_server/auth/erasure.py
  - tests/test_auth_api.py
  - docs/DATA_INVENTORY.md
autonomous: true
requirements:
  - R28B-01
  - R28B-02
  - R28B-03
must_haves:
  truths:
    - Full REST API for user management, API key CRUD, and role-based access
    - GDPR erasure workflow with state machine and tombstone pattern
    - Audit log with 90-day auto-prune
  artifacts:
    - path: "kb_server/auth/models.py"
      provides: "SQLAlchemy auth models"
      contains: "User, ApiKey, AuditLog, ErasureRequest"
      min_lines: 200
    - path: "kb_server/auth/router.py"
      provides: "Auth REST API endpoints"
      contains: "api/v1/users, api/v1/api-keys"
      min_lines: 100
    - path: "tests/test_auth_api.py"
      provides: "Auth test coverage"
      contains: "test_auth_service, test_deps, test_api, test_erasure"
      min_lines: 200
---

<objective>
Full REST API for user management, API key CRUD, SHA-256 hash storage, role-based access control (admin/user), and GDPR erasure workflow (active → requested → approved → completed tombstone pattern). Exposed via `/api/v1/users` and `/api/v1/api-keys` REST endpoints.

Purpose: Phase 28b provides the auth infrastructure needed by the Admin SPA (Phase 28c) and future API integrations. The REST API becomes the primary interface; existing CLI remains backward-compatible by calling the same service layer.

Output: SQLAlchemy models, AuthService CRUD, FastAPI dependency guards, REST router, GDPR ErasureManager, audit log auto-prune, and DATA_INVENTORY.md.
</objective>

<threat_model>
| ID | Threat | Impact | Mitigation |
|---|---|---|---|
| T-28b-01 | API key leakage via response bodies | High — leaked keys allow impersonation | Raw key returned only on creation; all subsequent responses return `prefix` only; `key_hash` never exposed |
| T-28b-02 | Unauthorized user creation / admin escalation | High — privilege escalation | Admin-only endpoints guarded by `require_admin` dependency; user creation rate not enforced yet |
| T-28b-03 | GDPR erasure bypass — skipping approval | High — legal non-compliance | State machine enforced in `ErasureManager`: `requested → approved → completed`. Each transition writes audit log; invalid transitions return False and reject |
| T-28b-04 | Audit log unbounded growth | Medium — disk exhaustion | 90-day auto-prune via `prune_audit_logs(days=90)`; configurable TTL |
| T-28b-05 | Deleted user access via stale API keys | Medium — data persistence | `verify_key` checks `is_active` and `erasure_status`; erased users always rejected even with valid hash |
</threat_model>

<tasks>

<task type="auto">
  <name>SQLAlchemy models for User, ApiKey, AuditLog, ErasureRequest</name>
  <files>kb_server/auth/__init__.py, kb_server/auth/models.py, tests/test_auth_api.py</files>
  <read_first></read_first>
  <action>
    Create `kb_server/auth/__init__.py` (empty) and `kb_server/auth/models.py` with async SQLAlchemy models:

    - `UserRole` enum: admin, user
    - `ErasureStatus` enum: active, erasure_requested, erasure_approved, erasure_completed, erasure_rejected
    - `Base` declarative base
    - `User`: UUID PK, username (unique), role, is_active, erasure_status, erasure_requested_at, erasure_approved_at, erasure_completed_at, created_at, updated_at. Relationships: api_keys (cascade delete), erasure_requests (cascade delete)
    - `ApiKey`: UUID PK, user_id FK (CASCADE), key_hash (SHA-256, unique), prefix, description, is_revoked, last_used_at, created_at
    - `AuditLog`: UUID PK, timestamp (indexed), actor_id (indexed), action, resource_type, resource_id, details
    - `ErasureRequest`: UUID PK, user_id FK (CASCADE), status, requested_by, approved_by, reason, created_at, resolved_at. Relationship: user
    - `create_tables(db_path)` factory

    Write failing tests for model creation, API key persistence, and cascade delete, then implement models.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_create_user -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - User model persists with auto-generated UUID, username, role, defaults
    - ApiKey model stores SHA-256 hash and prefix, never raw key
    - Deleting a User cascades to ApiKey and ErasureRequest
    - AuditLog records timestamped action entries
    - ErasureRequest tracks state machine transitions
    - `create_tables()` async creates all tables in SQLite
  </acceptance_criteria>
  <done>`kb_server/auth/models.py` and `__init__.py` created; model tests passing.</done>
</task>

<task type="auto">
  <name>Task 2: Auth service layer (CRUD)</name>
  <files>kb_server/auth/service.py, tests/test_auth_api.py</files>
  <read_first>kb_server/auth/models.py</read_first>
  <action>
    Create `kb_server/auth/service.py` with `AuthService` class:

    - `create_user(username, role)`: persists User, writes AuditLog `user.created`
    - `list_users()`: returns non-erased users ordered by created_at desc
    - `get_user(user_id)`: get by PK
    - `get_user_by_username(username)`: get by unique username
    - `create_api_key(user_id, description)`: generates `secrets.token_urlsafe(32)`, computes SHA-256 hash, stores ApiKey with prefix (first 8 chars), returns (raw_key, key_obj). Writes audit log
    - `list_api_keys(user_id)`: all keys for user, ordered desc
    - `revoke_api_key(key_id)`: sets is_revoked, writes audit log
    - `verify_key(raw_key)`: hashes input, looks up non-revoked key, checks user active + not erased, updates last_used_at, returns User or None

    Write failing tests for each CRUD operation, then implement service.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_auth_service_create_user -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - User creation writes audit log entry
    - API key generation returns raw key exactly once; stored hash is irreversible
    - Revoked keys fail verification
    - Erased user's keys fail verification
    - Listing excludes erased users
  </acceptance_criteria>
  <done>`kb_server/auth/service.py` created; all service CRUD tests passing.</done>
</task>

<task type="auto">
  <name>Task 3: FastAPI dependencies (guards)</name>
  <files>kb_server/auth/deps.py, tests/test_auth_api.py</files>
  <read_first>kb_server/auth/service.py</read_first>
  <action>
    Create `kb_server/auth/deps.py` with FastAPI dependency guards:

    - `api_key_header`: APIKeyHeader scheme for X-API-Key
    - `get_current_user(request, api_key)`: extracts key from header or Bearer token, delegates to AuthService.verify_key, raises 401 on failure
    - `require_admin(current_user)`: checks role == "admin", raises 403 otherwise
    - `require_auth(current_user)`: checks is_active, raises 401/403 otherwise

    Write failing tests for authentication and authorization guards, then implement.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_deps_get_current_user -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - Valid API key returns User from `get_current_user`
    - Missing/invalid key returns 401
    - Admin user passes `require_admin`; non-admin gets 403
    - Inactive user blocked by `require_auth`
  </acceptance_criteria>
  <done>`kb_server/auth/deps.py` created; dependency guard tests passing.</done>
</task>

<task type="auto">
  <name>Task 4: REST API router</name>
  <files>kb_server/auth/router.py, kb_server/auth/schemas.py, tests/test_auth_api.py</files>
  <read_first>kb_server/auth/deps.py</read_first>
  <action>
    Create `kb_server/auth/schemas.py` with Pydantic request/response models:

    - `CreateUserRequest`: username (str), role (str, default "user")
    - `UserResponse`: id, username, role, is_active, created_at
    - `CreateApiKeyRequest`: user_id, description
    - `ApiKeyResponse`: id, prefix, description, is_revoked, created_at (no key_hash)
    - `ApiKeyCreatedResponse(ApiKeyResponse)`: adds raw_key

    Create `kb_server/auth/router.py` with FastAPI APIRouter:

    - POST `/api/v1/users` — create user (checks duplicate username → 409)
    - GET `/api/v1/users` — list users
    - GET `/api/v1/users/me` — current user (requires auth)
    - DELETE `/api/v1/users/{user_id}` — soft delete (tombstone username, clear active)
    - POST `/api/v1/api-keys` — create key for user (checks user exists → 404)
    - GET `/api/v1/api-keys?user_id=` — list keys for user
    - DELETE `/api/v1/api-keys/{key_id}` — revoke key

    Write failing integration tests using httpx ASGITransport, then implement schemas and router.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_api_create_user -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - POST `/api/v1/users` returns UserResponse with 200; duplicate username returns 409
    - GET `/api/v1/users` returns list of users
    - GET `/api/v1/users/me` returns authenticated user
    - POST `/api/v1/api-keys` returns ApiKeyCreatedResponse with raw_key in body
    - GET `/api/v1/api-keys` returns keys without key_hash field
    - DELETE `/api/v1/api-keys/{key_id}` marks key revoked
  </acceptance_criteria>
  <done>`kb_server/auth/router.py` and `schemas.py` created; all API endpoint tests passing.</done>
</task>

<task type="auto">
  <name>Task 5: GDPR erasure workflow</name>
  <files>kb_server/auth/erasure.py, kb_server/auth/router.py, tests/test_auth_api.py</files>
  <read_first>kb_server/auth/service.py</read_first>
  <action>
    Create `kb_server/auth/erasure.py` with `ErasureManager`:

    - `request_erasure(user_id, requested_by, reason)`: creates ErasureRequest with status `erasure_requested`, writes audit log `user.erasure_requested`
    - `approve_erasure(request_id, approved_by)`: transitions from `erasure_requested` → `erasure_approved`, writes audit log. Returns False if invalid state
    - `execute_erasure(request_id)`: transitions from `erasure_approved` → `erasure_completed`. Anonymizes username to `deleted-user-{id[:8]}`, sets is_active=False, hard-deletes API keys, updates erasure_completed_at. Writes audit log. Returns False if invalid state

    Add to router:
    - POST `/api/v1/users/{user_id}/erasure-request` — submit erasure request
    - POST `/api/v1/admin/erasure-requests/{request_id}/approve` — approve and execute
    - GET `/api/v1/users/{user_id}/export` — export user data (GDPR right to data portability)

    Write failing tests for erasure workflow, then implement ErasureManager and endpoints.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_erasure_request_submit -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - Erasure request transitions through state machine: requested → approved → completed
    - Invalid state transitions return False
    - Each transition writes an audit log entry
    - After execution, user is anonymized (username changed, active=False)
    - After execution, all API keys are hard-deleted
    - Export endpoint returns user data without exposing hashes
  </acceptance_criteria>
  <done>`kb_server/auth/erasure.py` created; erasure workflow tests passing.</done>
</task>

<task type="auto">
  <name>Task 6: Audit log auto-prune</name>
  <files>kb_server/auth/service.py, tests/test_auth_api.py</files>
  <read_first>kb_server/auth/service.py</read_first>
  <action>
    Add `prune_audit_logs(days=90)` method to `AuthService`:

    - Computes cutoff timestamp: `datetime.utcnow() - timedelta(days=days)`
    - Executes `DELETE FROM audit_logs WHERE timestamp < cutoff`
    - Returns number of deleted rows

    Add `from sqlalchemy import delete as sa_delete` import to service.py.

    Write failing test that creates audit log entries, prunes with days=0, and verifies deletion count.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py::test_audit_prune -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `prune_audit_logs(days=90)` deletes entries older than 90 days
    - Returns count of deleted rows
    - Recent entries (within TTL) are preserved
    - Works with days=0 to delete all entries
  </acceptance_criteria>
  <done>Audit log auto-prune method added to AuthService; prune test passing.</done>
</task>

<task type="auto">
  <name>GDPR data inventory document</name>
  <files>docs/DATA_INVENTORY.md</files>
  <read_first></read_first>
  <action>
    Create `docs/DATA_INVENTORY.md` documenting all data stores for GDPR compliance:

    | Data Store | Data Categories | PII? | Retention | Deletion Method |
    | users table | username, role, timestamps | Pseudonymous | Indefinite → tombstone on erasure | Anonymize, clear active |
    | api_keys table | key_hash (SHA-256), prefix, timestamps | None | Until user erasure | Hard DELETE |
    | audit_logs table | actor_id (UUID), action, timestamp | None | 90 days auto-prune | Hard DELETE after TTL |
    | config table | key, value, type, group | None | Indefinite | Direct DELETE |
    | App logs | Request paths, response codes | None (IP stripped) | 30 days | Log rotation |
    | Qdrant vector store | Document chunks, metadata | None (product docs) | Indefinite | Collection drop |

    Include breach notification guidance referencing this inventory.
  </action>
  <verify>
    <automated>test -f docs/DATA_INVENTORY.md && echo "EXISTS"</automated>
  </verify>
  <acceptance_criteria>
    - All data stores are listed with categories, PII classification, retention, and deletion method
    - Breach notification reference included
    - Document is dated and maintained alongside auth package
  </acceptance_criteria>
  <done>`docs/DATA_INVENTORY.md` created and committed.</done>
</task>

<verification>
### Per-Task Verification
Each task has its own automated test verification (see `<verify>` blocks above). Tasks must pass before proceeding to the next.

### Full Test Suite
```bash
cd /home/admin/kb-rag-mcp && python -m pytest tests/test_auth_api.py -x -v 2>&1 | tail -20
```
Expected: All tests PASS

### Regression Check
```bash
cd /home/admin/kb-rag-mcp && python -m pytest -x --timeout=60 2>&1 | tail -20
```
Expected: No regressions in existing tests.

### Threat Mitigation Verification
- T-28b-01: Confirm no endpoint returns `key_hash` in response body; raw_key only in `ApiKeyCreatedResponse`
- T-28b-02: Confirm `require_admin` guard is applied to user creation endpoint (or documented as open)
- T-28b-03: Confirm state machine rejects invalid transitions by calling `approve_erasure` on already-completed request
- T-28b-04: Confirm `prune_audit_logs(days=90)` deletes only entries older than cutoff
- T-28b-05: Confirm `verify_key` returns None for erased users even with valid key hash
</verification>

<success_criteria>
- User management CRUD works via REST API
- API key lifecycle (create, list, revoke) is complete
- Role-based access guards (admin/user) block unauthorized actions
- GDPR erasure state machine correctly transitions and tombstones data
- Audit logs auto-prune after 90 days
- Data inventory document catalogs all PII stores
- All tests pass
</success_criteria>

<output>
After completion, create `.planning/phases/28b-auth-api/28b-01-SUMMARY.md`
</output>
