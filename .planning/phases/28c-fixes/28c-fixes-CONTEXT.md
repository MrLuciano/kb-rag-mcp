---
phase: 28c-fixes
name: Admin SPA Gap Closure
source: 28c-UAT.md, 28c-UI-REVIEW.md, 28c-UI-SPEC.md
date: 2026-06-16
---

# Phase 28c-fixes: Admin SPA Gap Closure — Context

**Status:** Gap closure phase for Phase 28c-admin-spa-panel UAT failures.
**Baseline:** All code exists in `kb_server/ui/templates/admin/` and `kb_server/ui/routes_admin.py`.

## Task Boundary

Fix the 9 UAT gaps identified in 28c-UAT.md so the Admin SPA matches the approved 28c-UI-SPEC.md.

## Implementation Decisions

### D-01: Auth Flow Fix (BLOCKER)
- Rewrite `shell.html:authenticate()` to POST `/api/v1/auth/session` with Bearer token
- Handle 200 (sets HttpOnly JWT cookie), 401, 403 responses
- Use Alpine.js `x-show="!isAuthenticated"` for login modal control (remove Bootstrap JS API)
- Logout clears localStorage AND calls logout endpoint to clear cookie
- 401 interceptor shows login modal

### D-02: Document Browse Features (HIGH)
- Add checkbox column with "select all" header to `_documents_table.html`
- Add bulk toolbar (Delete, Re-ingest, Delete Failed) visible when >=1 row selected
- Add per-document Actions dropdown (View, Delete, Re-ingest) with `hx-confirm`
- Selection state tracked in Alpine.js

### D-03: CSP / SRI Fixes (HIGH)
- Add `nonce="{{ get_nonce(request) }}"` to `tab_ragas.html:36` inline script
- Add `integrity` attribute to `login.html:7` Bootstrap CSS link
- These are one-line fixes; include in same plan as auth flow

### D-04: Monitor Lights Improvements (MEDIUM)
- Add LLM component (7th component) to `_monitor_lights.html`
- Add latency in ms below component names
- Add click-to-expand details toggle
- Add `aria-label` on status badges
- Add degraded/warning (yellow) state

### D-05: Config Editor Improvements (MEDIUM)
- Add "Reset All" button with `hx-confirm` to `_config_table.html`
- Change Group column from plain text to badge
- Switch save mechanism from `fetch()` to HTMX PUT
- Add `aria-live="assertive"` for error announcements

### D-06: Copy and Spacing Fixes (MEDIUM)
- Fix 12 label/empty-state mismatches documented in UI-REVIEW.md
- Change sidebar width from 220px to 280px
- Fix mobile responsive behavior (icon-only 60px at md, hamburger at sm)

### D-07: Missing Partials (MEDIUM)
- Create `_ingestion_manual.html`, `_ingestion_schedule.html`, `_ingestion_monitor.html`
- Create `_ragas_editor.html`, `_ragas_results.html`
- Update ingestion and RAGAS tabs to load partials instead of inline content

### D-08: Alpine.js Version (LOW)
- Upgrade from 3.13.3 to 3.14.8 CSP build (can defer)

## Canonical References

- `.planning/phases/28c-admin-spa-panel/28c-UI-SPEC.md` — Approved design contract (all fixes must match)
- `.planning/phases/28c-admin-spa-panel/28c-UI-REVIEW.md` — Detailed gap analysis with file:line references
- `.planning/phases/28c-admin-spa-panel/28c-UAT.md` — UAT test results and priorities
- `.planning/phases/28b-auth-api/28b-CONTEXT.md` — Auth design decisions (JWT session cookie model)

## Specific Ideas

- Auth endpoint `/api/v1/auth/session` already exists (per 28c-01 summary)
- Config endpoints already exist at `/api/v1/config`
- Document endpoints exist at `/api/v1/documents` and `/api/v1/ingest`
- Use existing `get_nonce(request)` helper from CSP middleware
- HTMX partial loading pattern already established in shell.html

## Deferred

- Alpine.js 3.14.8 upgrade (D-08) — not blocking, can be done as follow-up
- frame-src CSP tightening (too broad) — requires Grafana URL config, defer
