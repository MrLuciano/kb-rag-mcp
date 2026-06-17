# 28c-fixes-03 Summary: Auth Infrastructure Gaps

## One-liner
Mounted auth router on UI app, fixed Alpine.js CSP build URL, added server-side auth gating to all admin tab endpoints, seeded default admin account on startup.

## Tasks
- **Task 1** (auto): Fixed Alpine.js CDN URL from `alpinejs` (non-CSP) to `@alpinejs/csp` (CSP-safe), added correct SRI hash, added status-code-specific HTMX error handler messages (401/404/500/other)
- **Task 2** (auto): Mounted `auth_router` on UI app, added `ensure_admin_account()` to AuthService, startup event seeds admin user + API key with banner log
- **Task 3** (auto): Updated `get_current_user` to validate session cookies (HMAC-signed JWT), added `Depends(get_current_user)` to all 13 admin tab endpoints (excluding shell)
- **Task 4** (auto): Removed orphaned `login.html`, removed `/login` and `/auth/login` routes from app.py, removed orphaned `test_login_html_has_sri_integrity` test

## Verification
- Admin UI tests: 34 passed, 0 failed, 34 errors (pre-existing `/app` PermissionError)
- Auth router mounted (1 grep match), auth gating on 13 endpoints
- Flake8 clean on new code; all remaining issues pre-existing
- `login.html` verified removed
