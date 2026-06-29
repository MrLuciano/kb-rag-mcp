# Security Audit Report — kb-rag-mcp v0.1.5

**Audited by:** OpenCode security review  
**Date:** 2026-06-29  
**Scope:** Auth subsystem (`kb_server/auth/`, `kb_server/config/router.py`, `kb_server/schedules/router.py`, `kb_server/health_server.py`, `kb_server/server.py`)

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 1 |
| High     | 2 |
| Medium   | 4 |
| Low      | 3 |
| Info     | 2 |

**Threat model context:** This is a self-hosted internal tool. The risk surface assumes:
- Deployed on a private network (no public internet exposure)
- Used by engineering teams within a single organisation
- No regulatory compliance baseline (PCI, HIPAA, SOC2)
- Qdrant, the embedding backend (LM Studio/Ollama), and the auth DB file are co-located or on the same trusted network

---

## 1. API Key Management

### 1.1 Entropy — **Low**

API keys are generated with `secrets.token_urlsafe(32)` (256 bits) in the new `AuthService` (`kb_server/auth/service.py:229`) and `secrets.token_hex(32)` (also 256 bits) in the legacy `auth_registry` (`kb_server/auth_registry.py:120`). Both are cryptographically strong. The raw key is returned exactly once at creation and never stored — only the SHA-256 hash persists.

**Verdict:** Sufficient entropy for an internal tool. No change required.

### 1.2 Key hashing — **Low**

Keys are hashed with a single SHA-256 pass (`service.py:230`, `auth_registry.py:121`). While this means a DB compromise reveals key hashes, the 256-bit input entropy makes preimage or collision attacks impractical. A slow hash (bcrypt/Argon2) would be overkill for API keys since they are high-entropy secrets by construction.

**Verdict:** Acceptable for internal use. Defer PBKDF2-wrapping unless the threat model expands to public-facing deployment.

---

## 2. Session Token Entropy — **Medium**

Session cookies use HMAC-SHA256 but truncate the output to **16 hex characters (64 bits)** (`kb_server/auth/router.py:81`, `kb_server/auth/deps.py:73`).

```python
signature = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()[:16]
```

A 64-bit MAC does not provide a sufficient security margin against collision or forgery in high-traffic deployments. An attacker who observes many sessions could have a non-negligible chance of forging a valid token.

Additionally, the HMAC secret falls back to the hardcoded string `"kb-rag-mcp-session-secret"` when `JWT_SECRET` is unset (`router.py:78`, `deps.py:68`). This is identical in both files, but each file loads `JWT_SECRET` independently at module load time via `os.getenv("JWT_SECRET", "")`.

**Recommendation:**
- Increase the truncated signature to at least 32 hex characters (128 bits): `hexdigest()[:32]`
- Document that `JWT_SECRET` must be set to a cryptographically random value in production (e.g., `openssl rand -hex 32`)

---

## 3. Session Cookie Flags — **Medium**

Set in `kb_server/auth/router.py:84-91` and `router.py:134-141`:

| Flag | Value | Issue |
|------|-------|-------|
| `httponly` | `True` | Correct — prevents JS access |
| `samesite` | `"lax"` | Acceptable for internal tool |
| `secure` | `_JWT_SECURE` | **Defaults to `false`** — cookie sent over plain HTTP |
| `max_age` | `_SESSION_TIMEOUT` (1800s) | Reasonable default |
| `path` | `"/"` | Standard |

The `secure` flag defaulting to `false` means cookies are transmitted over unencrypted connections. For a self-hosted tool running on a LAN behind a VPN or Tailscale, this is low risk — but if anyone deploys it with a reverse proxy terminating TLS (which is common even for internal tools), the secure flag should reflect that.

**Recommendation:** Make `JWT_SECURE` default to `True` when running on non-localhost interfaces, or add an automatic check: if the request came over HTTPS, set secure. For v0.1.5, this is a documentation gap — add an `.env.example` comment that `JWT_SECURE=true` should be set when TLS is in use.

---

## 4. Rate Limiting — **High**

### 4.1 Auth endpoints have no rate limiting

`POST /api/v1/auth/login` (`kb_server/auth/router.py:61`) is completely unprotected. The `ServerRateLimiter` is only applied to MCP tool calls (`server.py:675`) and SSE/streamable-http connections (`server.py:1720`, `server.py:1854`). There is no rate limiting on:
- Login attempts (brute force / password spraying)
- API key creation/deletion
- Session creation
- User CRUD operations

For an internal tool this is situational, but a compromised internal machine could trivially brute force the default admin password "admin" (see finding 10).

**Recommendation:** Add per-IP rate limiting (e.g., 5 attempts/minute) to the `POST /auth/login` endpoint. Use `ServerRateLimiter` or a simple in-memory counter keyed on `request.client.host`.

### 4.2 stdio transport has no auth or rate limiting — **Critical**

The stdio transport (`server.py:1972-1975`) does not authenticate at all:

```python
_current_subject.set("stdio")
_current_transport.set("stdio")
async with stdio_server() as (read, write):
    await app.run(read, write, app.create_initialization_options())
```

The MCP protocol over stdio is designed for local spawning by trusted clients (Claude Code, OpenCode), so the lack of auth is architecturally correct — the parent process is responsible for access control. However, rate limiting still applies to tool calls when `RATE_LIMIT_ENABLED=True` (line 675 checks `rate_limiter` which is initialized in `main()` regardless of transport).

This is flagged as **Info / Accepted Risk** for the stdio use case, but any deployment exposing the SSE or streamable-http transports without additional firewall rules should disable stdio entirely.

---

## 5. PII Exposure — **Medium**

### 5.1 User list endpoint returns emails

`GET /api/v1/users` (`kb_server/auth/router.py:227`) returns `UserResponse` which includes `email` (schemas.py:22). This is gated behind `require_admin`, so only admins can list users with emails. For an internal tool, this is acceptable.

### 5.2 Audit log retention

Audit logs store `actor_id`, `action`, `resource_type`, `resource_id`, and optional `details` (`service.py:460-475`). The `prune_audit_logs` method (`service.py:477`) allows pruning older than N days (default 90). There is no automatic pruning — it must be called explicitly.

**Recommendation:** Add a periodic background task (similar to `_schedule_log_cleanup` for query logs) to auto-prune audit logs on a configurable retention schedule.

### 5.3 GDPR erasure completeness — **Medium**

`ErasureManager.execute_erasure` (erasure.py:85-123) anonymises the user record (`deleted-user-{short_id}`), deactivates the account, deletes API keys, and sets `erasure_completed`. However:

1. **Audit log entries referencing the user ID are NOT deleted** — entries in `audit_logs` with `actor_id = user.id` persist (erasure.py:115-121 adds a *new* entry but does not clean up old ones). This means a data subject's activity trail remains in the audit log even after erasure.
2. **User sessions are not cleaned up** — `user_sessions` table rows for this user remain (no cascade delete on the session relationship in `models.py`). The `UserSession` model has a FK to `users` with `ondelete="CASCADE"` only on the session's `user_id` column — but `delete_user` does not cascade; `execute_erasure` only deletes `api_keys`.
3. **The `delete_user` method** (`service.py:200-218`) also retains the anonymised user row but does not cascade-delete sessions or audit logs.

**Recommendation:** `execute_erasure` should also:
- Delete or anonymise `user_sessions` rows for the user
- Anonymise `audit_logs.actor_id` entries that match the user ID
- Delete or anonymise `erasure_requests` for the user (the request row itself persists)

For v0.1.5, document these gaps as known limitations.

---

## 6. SQL Injection Vectors — **Info**

All user-facing query parameters go through SQLAlchemy ORM queries with parameterised filters. The only raw SQL is in `AuthService._run_migrations` (`service.py:29-76`), which uses `sa_text()` with hardcoded column names and no user input.

The config values (`product`, `doc_type`, `version`, etc.) are passed as filter parameters to SQLAlchemy / Qdrant clients, which handle escaping natively.

**Verdict:** No injectable paths found. Low risk for an internal tool.

---

## 7. CORS Configuration — **Low**

CORS is configured only for the streamable-http transport (`server.py:1899-1912`):

```python
Middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=[...],
)
```

`allow_origins=["*"]` permits any website to make cross-origin requests. For an internal tool on a private network, this is low risk. However, if the server is ever exposed (even behind corporate SSO or a VPN), a malicious internal page could make API calls on behalf of a logged-in user (since the session cookie would be sent for credentialed requests).

**Recommendation:** Default `allow_origins` to the empty list `[]` or document that deployers should restrict it. For v0.1.5, add a `CORS_ORIGINS` env var defaulting to `""` (no CORS headers).

---

## 8. Authentication Bypass — **High**

### 8.1 `AUTH_ENABLED` global bypass

The `AUTH_ENABLED` environment variable (default: `"false"`) acts as a master kill-switch for authentication:

- `legacy.py:61` — `verify_request` returns `(True, None)` immediately when auth is disabled
- `config/router.py:82` — config API falls through to allow unauthenticated access when auth is disabled
- `server.py:1698` — SSE transport skips `verify_request` entirely when auth is disabled
- `server.py:1845` — Streamable HTTP transport skips auth when disabled

This is by design — it allows zero-config local development. However, the `AUTH_ENABLED` flag is read **once at module import time** (`legacy.py:20`) and cached for the process lifetime. There is no way to dynamically enable/disable auth without a restart.

**Risk:** An operator who sets up the server and forgets to set `AUTH_ENABLED=true` exposes the full API (config, schedules, user management) without any authentication.

**Recommendation:**
- Print a prominent warning on startup when `AUTH_ENABLED` is `false` (it currently only warns about embedding/Qdrant health, not auth)
- Consider requiring explicit consent: refuse to start in SSE/HTTP mode with auth disabled unless `AUTH_DISABLED_ACK=true` is also set

### 8.2 stdio transport has no authentication — **Info / Accepted Risk**

See finding 4.2. The stdio transport is architecturally correct — it trusts the parent process. Documented risk.

---

## 9. Authorization — **Low**

### 9.1 Admin gating is consistent

All admin-only endpoints use `require_admin` dependency (`deps.py:97`), which checks `current_user.role == "admin"`. Verified paths:

| Endpoint | Guard | File |
|----------|-------|------|
| `POST /api/v1/users` | `require_admin` | router.py:215 |
| `GET /api/v1/users` | `require_admin` | router.py:230 |
| `DELETE /api/v1/users/{id}` | `require_admin` | router.py:248 |
| `PATCH /api/v1/users/{id}` | `require_admin` | router.py:264 |
| `POST /admin/erasure-requests/{id}/approve` | `require_admin` | router.py:364 |
| `POST /admin/erasure-requests/{id}/execute` | `require_admin` | router.py:384 |
| `POST /auth/sessions/{id}/revoke` | `require_admin` | router.py:196 |
| All schedules CRUD | `require_admin` | schedules/router.py:60-139 |
| Config CRUD | `_verify_config_auth` | config/router.py:91 |

The config router uses a custom `_verify_config_auth` that authenticates via Bearer token, session cookie, or falls through if `AUTH_ENABLED=false`. It does **not** check for admin role — any valid user can modify configuration. This is a potential privilege escalation path (a regular user changing rate limits, query log settings, etc.).

**Recommendation:** Add role checking to `_verify_config_auth` — require admin role for config mutations (`PUT`, `DELETE`, `POST /reset`).

### 9.2 API key listing access control

`GET /api/v1/api-keys` (`router.py:307`) allows a user to list their own keys, or an admin to list any user's keys. The check at line 315 is correct: `if target_id != current_user.id and current_user.role != "admin"`. This is properly implemented.

---

## 10. Secrets Management — **High**

### 10.1 Default admin credentials are hardcoded

`service.py:352-408`:
```python
self.set_password(user_id, "admin")  # line 353
...
print(f"  Password: {admin}", flush=True)  # line 380
```

The default admin password is hardcoded as `"admin"`. It is printed to stdout and logged at startup. This is a well-known default credential.

**Risk:** If the server is started and operators fail to change the default password, any internal user who can reach the login endpoint can authenticate as admin.

**Recommendation:**
- Generate a random password on first boot and print it once (similar to how the API key is generated)
- Force password change on first login
- Or at minimum, add a prominent printed warning that the default password must be changed

### 10.2 `JWT_SECRET` fallback is hardcoded

When `JWT_SECRET` is not set, both `router.py:78` and `deps.py:68` fall back to `"kb-rag-mcp-session-secret"`. This is a known, hardcoded string — any session signed with this secret can be forged by anyone who reads the source code (which is public).

**Recommendation:** Refuse to start (or emit a critical warning) when `JWT_SECRET` is unset and `AUTH_ENABLED=true`.

### 10.3 `JWT_SECRET` is loaded twice at module level

`kb_server/auth/router.py:30` and `kb_server/auth/deps.py:19` both load `JWT_SECRET` independently at module import time. If one module is imported before the env var is set (e.g., due to import ordering), they could end up with different values.

**Recommendation:** Consolidate secret loading into a single location (e.g., `kb_server/auth/config.py`) to ensure a single source of truth.

### 10.4 API key exposed in logs and stdout

The raw API key is logged and printed to stdout during admin account seeding (`service.py:374-382`, `service.py:398-406`). This means plaintext keys appear in:
- `kb-mcp.log` (log file on disk)
- stderr/stdout (process output, potentially captured by systemd journal)

**Recommendation:** Log a message like `"Default API key created for admin"` without the actual key. Only print the key to stdout once if the process is interactive. For non-interactive deployments (systemd, Docker), log the prefix only.

---

## Remediation Plan (Critical / High)

### Critical — 4.2: stdio auth gap
**Already accepted by design.** No action needed beyond documentation.

### High — 4.1: No rate limiting on login
```python
# In kb_server/auth/router.py, add rate limiting to login_with_password:
from kb_server.rate_limiter import ServerRateLimiter

_login_limiter = None  # initialized in main() or lazily

@router.post("/auth/login")
async def login_with_password(request, response, body):
    # Add per-IP rate limit check
    if _login_limiter:
        ip = request.client.host if request.client else "unknown"
        allowed, retry_after = await _login_limiter.check(ip)
        if not allowed:
            raise HTTPException(status_code=429, detail="Too many login attempts")
    ...
```

### High — 7: CORS `allow_origins=["*"]`
```python
# In kb_server/server.py, change to:
CORS_ORIGINS = config.get("CORS_ORIGINS", "").split(",") if config.get("CORS_ORIGINS") else []
...
Middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else [],
    ...
)
```

### High — 8.1: `AUTH_ENABLED` warning
```python
# In server.py main(), after connecting vector store:
from kb_server.auth import is_auth_enabled
if TRANSPORT in ("sse", "streamable-http") and not is_auth_enabled():
    log.warning("=" * 60)
    log.warning("AUTHENTICATION IS DISABLED — set AUTH_ENABLED=true in .env")
    log.warning("The HTTP API has no authentication. Do not expose to untrusted networks.")
    log.warning("=" * 60)
```

### High — 10.1: Default admin password
```python
# In service.py ensure_admin_account / set_password:
# Generate a random password instead of hardcoding "admin"
import secrets
random_password = secrets.token_urlsafe(12)
self.set_password(user_id, random_password)
print(f"  Initial admin password: {random_password}")
```
Add a `FORCE_ADMIN_PASSWORD` env var for automated deployments to set a known password.

### High — 10.2: JWT_SECRET fallback
```python
# In deps.py and router.py:
_JWT_SECRET = os.getenv("JWT_SECRET")
if not _JWT_SECRET:
    if os.getenv("AUTH_ENABLED", "false").lower() in ("true", "1"):
        import sys
        print("FATAL: JWT_SECRET must be set when AUTH_ENABLED=true", file=sys.stderr)
        sys.exit(1)
    _JWT_SECRET = "kb-rag-mcp-session-secret"  # dev-only fallback
```

---

## Recommendations Summary (All Severities)

| # | Finding | Severity | Action |
|---|---------|----------|--------|
| 1 | Session token truncated to 64-bit HMAC | Medium | Increase to 128 bits (`[:16]` → `[:32]`) |
| 2 | `secure=False` on session cookies by default | Medium | Default to `True` or auto-detect HTTPS |
| 3 | No rate limiting on `/auth/login` | High | Add per-IP rate limiting to login endpoint |
| 4 | stdio transport has no auth | Critical | Accepted risk — document as expected |
| 5 | GDPR erasure leaves audit trail and sessions | Medium | Cascade-delete sessions, anonymise audit logs |
| 6 | CORS `allow_origins=["*"]` | Low | Make configurable via `CORS_ORIGINS` env var |
| 7 | `AUTH_ENABLED=false` bypasses all auth | High | Add startup warning when auth is disabled |
| 8 | Config router allows non-admin config changes | Medium | Add `require_admin` to config mutations |
| 9 | Hardcoded default admin password "admin" | High | Generate random password on first boot |
| 10 | `JWT_SECRET` fallback hardcoded in source | High | Require `JWT_SECRET` when auth is enabled |
| 11 | `JWT_SECRET` loaded independently in two modules | Low | Consolidate into single config module |
| 12 | API key printed to logs/stdout on creation | Low | Only log prefix; suppress raw key in logs |
| 13 | No auto-prune for audit logs | Low | Add background task to prune audit logs |
| 14 | No password strength validation | Info | Acceptable for internal tool; low priority |

---

## Files Audited

| File | Lines | Role |
|------|-------|------|
| `kb_server/auth/router.py` | 417 | API route handlers for auth, users, API keys, erasure |
| `kb_server/auth/deps.py` | 108 | FastAPI dependency injection: `get_current_user`, `require_admin` |
| `kb_server/auth/models.py` | 175 | SQLAlchemy models: User, ApiKey, AuditLog, ErasureRequest, UserSession |
| `kb_server/auth/service.py` | 502 | Business logic: password hashing, key management, user CRUD, sessions, audit |
| `kb_server/auth/legacy.py` | 82 | Legacy auth guard: `AUTH_ENABLED`, `verify_request`, backwards compat |
| `kb_server/auth/erasure.py` | 165 | GDPR erasure workflow: request → approve → execute |
| `kb_server/auth/__init__.py` | 18 | Package init, re-exports legacy functions |
| `kb_server/auth/schemas.py` | 78 | Pydantic request/response schemas |
| `kb_server/config/router.py` | 178 | Config API with custom auth |
| `kb_server/schedules/router.py` | 145 | Schedule CRUD with `require_admin` |
| `kb_server/health_server.py` | 171 | Health check server (no auth — by design) |
| `kb_server/server.py` | 1979 | Main MCP server: transport handling, auth integration, rate limiting |
| `kb_server/rate_limiter.py` | 110 | Token bucket rate limiter for MCP requests |
