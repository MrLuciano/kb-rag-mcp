# Phase 44: Auth Security Hardening - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix six auth infrastructure gaps identified in the REVIEW.md audit: mount the auth router, add erasure separation of duties, enforce ownership checks, secure session cookies, batch verify_key writes, and hash rate-limit subjects.

Requirements: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06

</domain>

<decisions>
## Implementation Decisions

### SEC-01: Mount Auth Router
- **D-01:** Mount the auth router (`router` from `kb_server/auth/router.py`) on the main FastAPI app in `kb_server/server.py` `main()`. Add `from kb_server.auth.router import router as auth_router` and `app.include_router(auth_router)`.

### SEC-02: Erasure Separation of Duties
- **D-02:** Split the single `approve_erasure` endpoint into two: `POST /admin/erasure-requests/{request_id}/approve` (approves only) and `POST /admin/erasure-requests/{request_id}/execute` (executes approved erasure). Call `mgr.approve_erasure()` in the approve endpoint and `mgr.execute_erasure()` in the execute endpoint. Both require `admin` role.

### SEC-03: Ownership Checks
- **D-03:** `list_api_keys` in `kb_server/auth/router.py` — change `user_id` query param to use `current_user.id` instead of accepting an arbitrary `user_id`. Non-admin users can only list their own keys.
- **D-04:** `export_user_data` in `kb_server/auth/router.py` — add check: if `current_user.id != user_id` and `current_user.role != 'admin'`, raise 403.

### SEC-04: Secure Cookie Flag
- **D-05:** In `kb_server/auth/router.py` session endpoint, gate `secure=True` on env var: `secure = os.getenv("JWT_SECURE", "false").lower() in ("true", "1")`. Pass this to `response.set_cookie(secure=secure)`.

### SEC-05: verify_key Write Batching
- **D-06:** Remove `api_key.last_used_at = datetime.utcnow()` and `self._session.commit()` from `verify_key()` in `kb_server/auth/service.py`. Add a separate `record_key_usage(key_id)` method called explicitly from the session endpoint only (not on every API key check).

### SEC-06: Rate-Limit Subject Hashing
- **D-07:** In `kb_server/server.py`, hash the subject token before passing to rate limiter. Use `hashlib.sha256(subject.encode()).hexdigest()[:16]` to produce a stable, non-reversible subject identifier.

### the agent's Discretion
- Migration path for any clients relying on the old erasure endpoint
- Logging level for ownership check failures
- Whether to add tests for each of the 6 fixes

</decisions>

<canonical_refs>
## Canonical References

- `kb_server/auth/router.py` — Auth endpoints to fix
- `kb_server/auth/service.py` — verify_key fix
- `kb_server/auth/erasure.py` — ErasureManager for separation
- `kb_server/server.py` — Auth router mount + rate-limit subject hashing
- `.planning/ROADMAP.md` §Phase 44 — Phase goal, success criteria
</canonical_refs>

<deferred>
## Deferred Ideas

None — all 6 items are in scope for this phase.

</deferred>

---

*Phase: 44-auth-security-hardening*
*Context gathered: 2026-06-15*
