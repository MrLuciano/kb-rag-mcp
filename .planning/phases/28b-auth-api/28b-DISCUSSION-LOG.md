# Phase 28b: Auth & User Management API - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 28b-auth-api
**Areas discussed:** Post-execution context capture (phase already implemented)

---

## Note: Phase Already Executed

This discussion was run AFTER Phase 28b was fully implemented. The purpose was to capture design decisions from the existing code into CONTEXT.md for downstream phases that depend on auth (Phase 28c Admin SPA, Phase 38 Grafana, Phase 41 Provider Aliases).

**Execution status:**
- Plan 28b-01: 6/6 tasks complete
- Tests: 37/37 auth API tests + 21/21 backward compat tests passing
- Code: 1,013 lines across `kb_server/auth/` module
- Linting: flake8, black, isort all clean

**Decisions inferred from code review:**

| Decision | Implementation |
|----------|---------------|
| Database | Separate `data/auth.db` SQLite (not `kb_metadata.db`) |
| PKs | UUID String(36) for all entities |
| Timestamps | Timezone-naive UTC for SQLite compatibility |
| Session token | HMAC-SHA256 signed (not JWT), 8h HttpOnly cookie |
| API key storage | SHA-256 hash + 8-char prefix; raw key shown once on creation |
| Auth header | `X-API-Key` OR `Authorization: Bearer` |
| Roles | Enum: "admin", "user" |
| Erasure states | 5-state machine on User model + ErasureRequest table |
| Delete user | Tombstone: anonymize username, deactivate, preserve UUID |
| Audit log | Auto-prune after 90 days |
| Service pattern | AuthService + ErasureManager with shared SQLAlchemy session |
| Legacy compat | Old `auth.py` → `auth/legacy.py`, re-exported via `__init__.py` |

---

## the agent's Discretion

- Pagination for list_users() — not implemented
- Rate limiting on auth endpoints — handled by Phase 33 global rate limiter
- API key rotation — not implemented

## Deferred Ideas

- OAuth/SSO integration (out of scope per REQUIREMENTS.md)
- Multi-factor auth (out of scope per REQUIREMENTS.md)
- Real-time audit log streaming
