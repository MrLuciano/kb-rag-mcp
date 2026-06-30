---
status: done
phase: 28c-fixes
source: 28c-fixes-01-SUMMARY.md, 28c-fixes-02-SUMMARY.md, 28c-fixes-03-SUMMARY.md, 28c-fixes-04-SUMMARY.md, 28c-fixes-05-SUMMARY.md
started: 2026-06-23T16:00:00Z
updated: 2026-06-23T20:31:00Z
---

## Resolution

**Root cause:** The server runs inside a Docker container (`kb-web-ui`) with `/home/admin/kb-rag-mcp/data` bind-mounted to `/app/data`. Deleting `auth.db` on the host unlinked the file that the running server's SQLite connection held open, causing `sqlite3.OperationalError: attempt to write a readonly database` on all auth endpoints.

**Fix:** `docker compose -f /home/admin/kb-rag-mcp/docker-compose.yml restart web-ui` — recreated `auth.db` and seeded admin account.

## Verification

### 1. Password login with admin/admin
curl POST /api/v1/auth/login {"username":"admin","password":"admin"}
Result: `HTTP 200` with session token `{"id":"795764d6","username":"admin","role":"admin","token_type":"Bearer","expires_in":1800}`

### 2. API key login
curl POST /api/v1/auth/session -H "Authorization: Bearer <key>"
Result: `HTTP 200` with session cookie set, `{"id":"795764d6","username":"admin","role":"admin","token_type":"Bearer","expires_in":1800}`

### 3. Session validation
curl GET /api/v1/users/me -b session_cookie
Result: `HTTP 200` with user info

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0
