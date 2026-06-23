---
phase: 28c-fixes
slug: admin-spa-fixes
status: compliant
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-23
---

# Phase 28c-fixes — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (asyncio_mode=strict) |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_admin_ui.py tests/test_auth_api.py -v -k "monitor or config or route or sidebar or ensure_admin"` |
| **Full suite command** | `pytest tests/test_admin_ui.py tests/test_ui_routes.py tests/test_auth_api.py -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_admin_ui.py -v`
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Requirement | Test Class | Automated Command | Status |
|---------|------|-------------|------------|-------------------|--------|
| Plan01-T1 | 01 | Auth flow rewrite — Alpine login overlay, authenticate(), logout(), 401 → CustomEvent | TestAuthFlow | `pytest tests/test_admin_ui.py -v -k 'auth or login'` | ✅ green |
| Plan01-T2 | 01 | Document browse selection + bulk actions — checkbox, selectAll, toggleDoc, hx-confirm | TestDocTable | `pytest tests/test_admin_ui.py -v -k 'doc_table'` | ✅ green |
| Plan01-T3 | 01 | CSP/SRI fixes — nonce on tab_ragas, SRI on Bootstrap CSS | (inline) | `pytest tests/test_admin_ui.py -v -k 'csp or nonce or integrity'` | ✅ green |
| Plan02-T1 | 02 | Complete monitor lights bar — LLM, latency, click-to-expand, ARIA, warning state | TestMonitorLights | `pytest tests/test_admin_ui.py -v -k 'monitor'` | ✅ green |
| Plan02-T2 | 02 | Improve config inline editor — Reset All hx-confirm, Group badges, HTMX PUT, aria-live, search placeholder | TestConfigEditor | `pytest tests/test_admin_ui.py -v -k 'config'` | ✅ green |
| Plan02-T3 | 02 | Create 5 missing partials + responsive sidebar (280px, md icon-only, sm hamburger, ARIA) | TestSidebarLayout | `pytest tests/test_admin_ui.py -v -k 'sidebar'` | ✅ green |
| Plan02-T4 | 02 | Fix route ordering — specific /tabs/ before generic /tabs/{tab_name} | TestRouteOrdering | `pytest tests/test_admin_ui.py -v -k 'route'` | ✅ green |
| Plan03-T1 | 03 | Alpine.js CSP build URL — @alpinejs/csp CDN with SRI | (inline) | `pytest tests/test_admin_ui.py -v -k 'integrity'` | ✅ green |
| Plan03-T2 | 03 | Mount auth_router + seed admin account — ensure_admin_account() startup event | TestAuthService | `pytest tests/test_auth_api.py -v -k 'ensure_admin'` | ✅ green |
| Plan03-T3 | 03 | Auth gating on admin tab endpoints — Depends(get_current_user) on all tab routes | (inline) | `pytest tests/test_admin_ui.py -v -k 'admin_documents or admin_ingestion or admin_ragas'` | ✅ green |
| Plan03-T4 | 03 | Remove orphaned login artifacts — login.html deleted | (inline) | `pytest tests/test_admin_ui.py -v -k 'shell'` | ✅ green |
| Plan04-T1 | 04 | UserSession model + session timeout — SESSION_TIMEOUT env var, expiry check | TestSessionManagement | `pytest tests/test_admin_ui.py -v -k 'session_timeout'` | ✅ green |
| Plan04-T2 | 04 | Session list/revoke + credentials UI — sessions table, revoke button, credentials section | TestSessionManagement + TestCredentialsSection | `pytest tests/test_admin_ui.py -v -k 'session or credential'` | ✅ green |
| Plan05-T1 | 05 | Alpine CSP build registration — x-data="adminApp" (no parens), alpine:init event listener | TestAuthFlow | `pytest tests/test_admin_ui.py -v -k 'alpine_xshow'` | ✅ green |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
