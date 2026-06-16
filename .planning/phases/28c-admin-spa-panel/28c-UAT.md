---
status: incomplete
phase: 28c-admin-spa-panel
source: 28c-UI-REVIEW.md, 28c-UI-SPEC.md
started: 2026-06-16
updated: 2026-06-16
---

## Verification Method

Verification performed via UI audit (gsd-ui-auditor) against approved 28c-UI-SPEC.md.
Score: **12/24** — significant gaps remain before shipping.

## Tests

### 1. Auth Flow (SPA-02, SPA-03, SPA-12)
expected: |
  User enters API key → POST /api/v1/auth/session → receives HttpOnly JWT session cookie (8h, SameSite=Lax) → authenticated for duration.
  Logout clears localStorage + cookie. 401 interceptor shows login modal.
result: fail
notes: |
  BLOCKER: Frontend never calls /api/v1/auth/session. Instead stores raw API key in localStorage
  and uses Bearer token on every request. JWT session cookie exchange is completely unused.
  Login modal controlled by Bootstrap JS instead of Alpine.js x-show.
  Impact: Different (less secure) auth model than designed.

### 2. Document Browse Table (SPA-09)
expected: |
  Checkbox column with "select all" header. Bulk toolbar appears when ≥1 row selected
  (Delete, Re-ingest, Delete Failed). Per-document Actions dropdown (View, Delete, Re-ingest).
  Delete with hx-confirm.
result: fail
notes: |
  Entire SPA-09 feature set missing. Only a "View" button exists.
  No checkboxes, no bulk toolbar, no per-doc dropdown, no delete/re-ingest actions.

### 3. Monitor Lights (SPA-06)
expected: |
  7 components (Qdrant, Embedding, LLM, Cache, Database, Filesystem, Grafana).
  Auto-refresh every 30s. Latency in ms below name. Click to expand/collapse details.
  ARIA labels on status badges.
result: partial
notes: |
  Auto-refresh works (hx-trigger="every 30s"). Missing LLM component (only 6 shown).
  No latency display. No click-to-expand details. No ARIA labels on badges.
  Missing degraded/warning (yellow) state — only green/red/gray.

### 4. Config Inline Editing (SPA-08)
expected: |
  Search filter, double-click to edit, save on Enter/Blur, cancel on Escape.
  "Reset All" button with hx-confirm. Type badges. Group badges. HTMX PUT.
result: partial
notes: |
  Search, dblclick edit, Enter/Blur save, Escape cancel — all present and working.
  Missing "Reset All" button. Group column shows plain text instead of badge.
  Uses fetch() instead of HTMX PUT. Error handling uses d-none toggle instead of aria-live.

### 5. Profile Tab (SPA-07)
expected: |
  Account info (username, role, created). API keys table with prefix/created/status/revoke.
  "Generate New Key" with Copy button. GDPR Export. Erasure with confirm dialog.
result: partial
notes: |
  Account info, API keys table, Generate New Key, GDPR Export, Erasure — all present.
  Missing "Copy" button for one-time key reveal. Extra "Config" section not in spec.
  Profile status uses text-* instead of bg-* badge styling.

### 6. Tab Navigation (SPA-04, SPA-05)
expected: |
  URL hash history updates on tab switch. Server-side role gating.
  Active tab indicator with Bootstrap nav-pills.
result: partial
notes: |
  Active tab indicator works (nav-pills active class). No URL hash history.
  Role gating is client-side only (x-show="isAdmin").

### 7. Security / CSP
expected: |
  Strict CSP with nonces on all inline scripts. SRI on all external resources.
  Alpine.js 3.14.8 CSP build. frame-src restricted to grafana URL.
  aria-live regions on HTMX targets.
result: fail
notes: |
  tab_ragas.html:36 script lacks CSP nonce — will be blocked by browser.
  login.html:7 loads Bootstrap CSS without integrity attribute.
  Alpine.js 3.13.3 loaded instead of spec's 3.14.8.
  frame-src 'self' https: is too broad (spec: https://{grafana_url} only).
  No aria-live regions on HTMX target containers.

### 8. Copywriting & Spacing
expected: |
  Matches UI-SPEC.md for all labels, empty states, placeholders, tab names.
  Sidebar 280px, icon-only 60px at md, hamburger at sm.
result: partial
notes: |
  Multiple mismatches: "Authentication Required" vs "Login to Admin Panel",
  "Evaluation" vs "RAGAS Evaluation", "Settings" vs "Admin".
  Sidebar 220px instead of 280px. Mobile is column stack instead of icon-only/hamburger.
  12 copy/spacing mismatches documented in UI-REVIEW.md.

### 9. Missing Partials
expected: |
  _ingestion_manual.html, _ingestion_schedule.html, _ingestion_monitor.html,
  _ragas_editor.html, _ragas_results.html exist and are loaded by tabs.
result: fail
notes: |
  None of these partials exist. Ingestion and RAGAS tabs use inline content instead.

## Summary

total: 9
passed: 0
partial: 4
failed: 5
blocked: 0

## Priority Fixes

### BLOCKER (must fix before shipping)
1. **Auth flow**: Rewrite authenticate() to POST /api/v1/auth/session, handle JWT cookie,
   use Alpine.js x-show for modal control.

### HIGH (should fix before shipping)
2. **Document browse**: Add checkbox column, bulk toolbar, per-doc Actions dropdown.
3. **CSP nonce**: Add nonce to tab_ragas.html script.
4. **SRI**: Add integrity to login.html Bootstrap CSS.

### MEDIUM (polish — can defer)
5. **Monitor lights**: Add LLM component, latency, details toggle, ARIA labels.
6. **Config editor**: Add "Reset All", Group badges, switch to HTMX PUT.
7. **Copy/spacing**: Fix 12 label/width/mobile mismatches.
8. **Missing partials**: Create _ingestion_*, _ragas_* partials.
9. **Alpine.js version**: Upgrade to 3.14.8 CSP build.

## Recommendation

Phase 28c core shell is functional but diverges significantly from spec.
Do NOT ship without fixing the auth flow BLOCKER.
Remaining items can be addressed in follow-up plans (28c-05 through 28c-08).
