# Phase 28b: Auth & User Management API - Context

**Gathered:** 2026-06-15
**Status:** Executed — all 6 tasks complete, 58/58 tests passing

<domain>
## Phase Boundary

Full REST API for user management, API key CRUD, role-based access control (admin/user), and GDPR-compliant erasure workflow — exposed via `/api/v1/users` and `/api/v1/api-keys` REST endpoints.

Requirements: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09, AUTH-10, AUTH-11, AUTH-12, AUTH-13, AUTH-14, AUTH-15

**Phase is EXECUTED.** All code exists in `kb_server/auth/` (1,013 lines). This CONTEXT.md documents the design decisions for downstream phases that depend on auth (Phase 28c Admin SPA, Phase 38 Grafana, Phase 41 Provider Aliases).

</domain>

<decisions>
## Implementation Decisions

### Database & Models
- **D-01:** Separate SQLite database: `data/auth.db` (not `kb_metadata.db`). Auth data is isolated from query logs and config.
- **D-02:** SQLAlchemy declarative_base with timezone-naive UTC timestamps for SQLite compatibility.
- **D-03:** All primary keys are UUID String(36) with `uuid.uuid4()` default — User, ApiKey, AuditLog, ErasureRequest.
- **D-04:** User.username is indexed and unique. User.role is String(20) with `UserRole` enum ("admin", "user").
- **D-05:** Erasure status stored ON the User model (`erasure_status` column) + separate `ErasureRequest` table for audit trail. States: `active → erasure_requested → erasure_approved → erasure_completed` (with `erasure_rejected` as terminal failure state).
- **D-06:** ApiKey stores SHA-256 `key_hash` (never exposed), 8-char `prefix` (shown in UI), `is_revoked` flag, `last_used_at` timestamp.
- **D-07:** Foreign keys use `ondelete="CASCADE"` — deleting a user cascades to API keys and erasure requests.

### Authentication & Session
- **D-08:** Session token is HMAC-SHA256 signed (NOT JWT). Format: `{user_id}:{expires_at}:{signature}` where signature is HMAC-SHA256(secret, raw)[:16].
- **D-09:** Session cookie: HttpOnly, SameSite=Lax, max_age=28800 (8h), secure flag controlled by `JWT_SECURE` env var.
- **D-10:** API key passed via `X-API-Key` header OR `Authorization: Bearer <key>` header. `deps.py` checks both.
- **D-11:** Session secret from `JWT_SECRET` env var; if unset, generates a random 32-byte hex fallback per restart.

### Authorization (FastAPI Depends)
- **D-12:** Dependency chain: `get_current_user` → `require_admin` / `require_auth`
  - `get_current_user`: Validates API key, returns User model, checks `is_active` and `erasure_status`
  - `require_admin`: Returns 403 if role != "admin"
  - `require_auth`: Returns 403 if `is_active` is False
- **D-13:** Admin endpoints: `POST /users`, `GET /users`, `DELETE /users/{id}`, `POST /admin/erasure-requests/{id}/approve`, `POST /admin/erasure-requests/{id}/execute`
- **D-14:** Self-service endpoints: `GET /users/me`, `GET /api-keys`, `POST /api-keys`, `DELETE /api-keys/{id}`, `POST /users/{id}/erasure-request`, `GET /users/{id}/export`

### API Key Lifecycle
- **D-15:** Raw API key returned ONLY on creation (`ApiKeyCreatedResponse.raw_key`). After that, only prefix + metadata are visible.
- **D-16:** Key verification checks `key_hash` against SHA-256 of provided key. Revoked keys fail verification.
- **D-17:** `record_key_usage()` updates `last_used_at` timestamp on successful verification.

### User Deletion (Tombstone)
- **D-18:** "Delete" is a tombstone operation: username → `deleted-user-{short_id}`, `is_active = False`, API keys deleted. UUID preserved for referential integrity.
- **D-19:** Erased users (status = `erasure_completed`) are excluded from `list_users()` and blocked from `verify_key()`.

### GDPR Erasure Workflow
- **D-20:** Three-step state machine enforced by `ErasureManager`:
  1. `request_erasure()` — creates ErasureRequest, sets `erasure_status = erasure_requested`
  2. `approve_erasure()` — admin approves, sets `erasure_status = erasure_approved`
  3. `execute_erasure()` — admin executes, sets `erasure_status = erasure_completed`, anonymizes user
- **D-21:** Invalid transitions return `False` (e.g., approving an already-approved request).
- **D-22:** Data export (`export_user_data`) returns JSON with user, API keys, audit logs, erasure requests.

### Audit Logging
- **D-23:** Every mutating operation writes an `AuditLog` entry: user create, API key create/revoke, erasure request/approve/execute, user delete.
- **D-24:** Auto-prune after 90 days via `prune_audit_logs(days=90)`.

### Service Architecture
- **D-25:** `AuthService` is the single entry point for all auth operations. Initialized with `db_path: Path`.
- **D-26:** `AuthService.session` is exposed as a property so `ErasureManager` can share the same SQLAlchemy session.
- **D-27:** FastAPI router gets `AuthService` from `request.app.state.auth_service` (injected at app startup).

### Legacy Compatibility
- **D-28:** Old `kb_server/auth.py` moved to `kb_server/auth/legacy.py`. `__init__.py` re-exports for backward compatibility.

### the agent's Discretion
- Pagination approach for `list_users()` — currently returns all; add pagination later if needed
- Rate limiting on auth endpoints — currently handled by Phase 33 global rate limiter
- API key rotation strategy — not implemented; users must revoke + create new

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Auth Module
- `kb_server/auth/models.py` — SQLAlchemy models: User, ApiKey, AuditLog, ErasureRequest, UserRole, ErasureStatus
- `kb_server/auth/service.py` — AuthService: user CRUD, API key lifecycle, verify_key, prune_audit_logs
- `kb_server/auth/deps.py` — FastAPI dependencies: get_current_user, require_admin, require_auth
- `kb_server/auth/router.py` — FastAPI APIRouter with all endpoints
- `kb_server/auth/schemas.py` — Pydantic request/response models
- `kb_server/auth/erasure.py` — ErasureManager: state machine + export
- `kb_server/auth/legacy.py` — Backward-compatible re-exports

### Database
- `data/auth.db` — SQLite auth database (separate from kb_metadata.db)

### Integration Points
- `kb_server/server.py` — Auth router mounted on FastAPI app
- `kb_server/ui/routes_admin.py` — Admin SPA uses auth endpoints
- `kb_server/ui/templates/admin/shell.html` — Alpine.js auth flow calls `/api/v1/auth/session`

### Planning Artifacts
- `.planning/phases/28b-auth-api/28b-01-PLAN.md` — Original plan (7 tasks)
- `.planning/phases/28b-auth-api/28b-01-SUMMARY.md` — Execution summary
- `.planning/REQUIREMENTS.md` §Auth & User Management API — AUTH-01 through AUTH-15

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AuthService` — Can be instantiated with any `Path` for testing or multi-tenant scenarios
- `ErasureManager` — Reusable GDPR erasure pattern for other entities
- `AuditLog` model — Can be extended for other operations (config changes, document deletions)
- FastAPI dependency guards — `require_admin`, `require_auth` reusable on any endpoint

### Established Patterns
- **Service + Manager pattern**: AuthService owns CRUD, ErasureManager owns workflow state machine
- **HMAC session tokens**: `{user_id}:{expires_at}:{signature}` — simpler than JWT, no external lib needed
- **Tombstone deletion**: Anonymize + deactivate + preserve UUID — used for GDPR compliance
- **Audit logging**: Every mutation writes AuditLog entry with actor, action, resource_type, resource_id

### Integration Points
- `kb_server/server.py` — Auth router mounted alongside health and MCP routes
- `kb_server/ui/app.py` — Admin SPA server injects `auth_service` into app.state
- Phase 28c Admin SPA — Calls auth endpoints for login, API key management, profile
- Phase 40 Config API — May need admin-only config endpoints (reuse `require_admin`)

</code_context>

<specifics>
## Specific Ideas

- Auth module uses its own `data/auth.db` — WAL mode should be enabled (AUTH-14 prerequisite)
- `JWT_SECRET` env var must be set in production or sessions are insecure (fallback uses random hex per restart)
- `JWT_SECURE` env var controls cookie `secure` flag — set to "true" for HTTPS deployments
- API keys are 32-byte random hex strings (64 chars raw, SHA-256 hashed for storage)
- All timestamps are timezone-naive UTC — consistent with SQLite limitations

</specifics>

<deferred>
## Deferred Ideas

- API key rotation endpoint (currently: revoke + create new)
- OAuth/SSO integration (out of scope per REQUIREMENTS.md)
- Multi-factor auth (out of scope per REQUIREMENTS.md)
- Real-time audit log streaming to external SIEM

</deferred>

---

*Phase: 28b-auth-api*
*Context gathered: 2026-06-15 (post-execution capture)*
