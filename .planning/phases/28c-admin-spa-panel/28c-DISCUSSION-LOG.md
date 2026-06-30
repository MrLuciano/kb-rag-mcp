# Phase 28c: Admin SPA Panel - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 28c-admin-spa-panel
**Areas discussed:** Auth flow, Tab loading & refresh, Monitor lights, Document browse, CSP/Security, Document export

---

## Auth Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Add session endpoint | POST /api/v1/auth/session; HttpOnly JWT cookie | ✓ |
| localStorage only | Store key in localStorage, Bearer on every request | |
| Hybrid Bearer + session | Both approaches for flexibility | |

**User's choice:** Add session endpoint

---

## Auth Re-entry

| Option | Description | Selected |
|--------|-------------|----------|
| 401 interceptor + login modal | HTMX catches 401, shows login modal | ✓ |
| Page reload to login | Redirect to /admin/login | |
| Session refresh silently | Transparent refresh using stored key | |

**User's choice:** 401 interceptor + login modal

---

## Tab Loading & Refresh

| Option | Description | Selected |
|--------|-------------|----------|
| HTMX partials + auto-refresh | hx-get per tab, auto-refresh on intervals | ✓ |
| Single-page full load | All content in shell template at once | |
| Alpine.js SPA with fetch | Client-side fetch + x-html rendering | |

**User's choice:** HTMX partials + auto-refresh

---

## Monitor Lights Design

| Option | Description | Selected |
|--------|-------------|----------|
| HTMX auto-poll + colored dots | hx-trigger every 30s, colored dot per component | ✓ |
| SSE stream | Server-Sent Events for real-time | |
| Static + manual refresh | Load on visit, manual refresh button | |

**User's choice:** HTMX auto-poll + colored dots

---

## Document Browse Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Table + filter bar + pagination | Sortable table, filter bar, 25/page | ✓ |
| Card grid + search | Card layout with typeahead | |
| Table + infinite scroll | Continuous scroll loading | |

**User's choice:** Table + filter bar + pagination

---

## CSP & Security

| Option | Description | Selected |
|--------|-------------|----------|
| Strict CSP with nonces | Alpine.js CSP build, nonce-based, SRI hashes | ✓ |
| Moderate CSP | Hash-based, CDN domains in script-src | |
| Minimal CSP | Default-src restrictions only | |

**User's choice:** Strict CSP with nonces

---

## Document Export

| Option | Description | Selected |
|--------|-------------|----------|
| Synchronous download | Export returns file directly | ✓ |
| Background job with progress | Async job with progress indicator | |
| Polling with fallback | Fast path sync, fallback to background | |

**User's choice:** Synchronous download

---

## the agent's Discretion

- Bootstrap 5 theme customization details
- Mobile responsiveness approach
- Nonce generation implementation
- HTMX event names and Alpine.js component structure

## Deferred Ideas

- Advanced filters (28c-03) and document export (28c-04) deferred to future plans
- SSE-based real-time design considered but rejected in favor of HTMX polling
- Background jobs for large exports deferred
