# Phase 53: v0.1.5 Quality & Polish — Context

**Gathered:** 2026-06-29
**Status:** Ready for planning
**Source:** User requirements

## Phase Boundary

Comprehensive quality pass on all v0.1.5 features before milestone closure. This phase covers five workstreams: bug fixing, test coverage, security review, documentation, and performance optimization.

## Implementation Decisions

### BugBash (Admin SPA & Backend)
- Systematic testing of Admin SPA: auth flow (login, logout, session timeout), config editor (CRUD, reset, hot-reload), document browse (filters, pagination, export), monitor lights (all 7 components), schedule management (CRUD, enable/disable, cron matching)
- Test all auth endpoints: session creation/refresh/revocation, API key CRUD, user CRUD, GDPR erasure workflow
- Test ingestion flows: manual ingestion from Monitor tab, scheduled ingestion from Schedule tab, progress tracking
- Fix all discovered bugs — prioritization: P0 (crash/data loss) > P1 (incorrect behavior) > P2 (UI glitches/cosmetic)

### E2E Tests
- Auth flow E2E: API key login → session cookie → authenticated requests → session refresh → logout
- Admin panel E2E: config CRUD, document browse with filters, document export (CSV/JSON), monitor lights rendering
- Schedule management E2E: create schedule → enable/disable → verify cron matching → verify job creation
- Use pytest + httpx AsyncClient for HTTP-level tests; could also add Selenium/Playwright for browser-level if appropriate

### Security Audit
- Auth endpoints: verify key hashing (SHA-256 for API keys, bcrypt/argon2 for passwords), session token entropy, CSRF protection
- Session cookie hardening: Secure flag, HttpOnly, SameSite, max-age
- Rate limiting effectiveness on auth endpoints (login, verify_key)
- PII exposure audit: user listing endpoints, audit log, GDPR erasure completeness
- Injection vectors: API key input, config value input, search queries

### Documentation
- README.md: Update with new features (Admin SPA, Auth API, Schedule Management, Grafana Embed)
- OPERATIONS.md: Document configuration env vars, auth setup, admin account seeding, schedule management
- Add API reference for Auth API endpoints and Config API endpoints
- Update deployment docs with new config requirements

### Performance Tuning
- Profile ConfigLoader hot-reload path (version check frequency, cache efficiency)
- Profile schedule background scheduler (cron matching, job creation, SQLite access pattern)
- Profile Admin SPA page loads (monitor lights refresh, document browse query times)
- Profile auth verify_key path (hash lookup, session validation)
- Optimize top-3 bottlenecks identified

## Canonical References

### Code Locations
- `kb_server/server.py` — Main server, tool handlers, MCP dispatch
- `kb_server/auth/` — Auth models, routers, middleware
- `kb_server/collections/` — Collection management
- `kb_server/config/` — ConfigLoader, config router, hot-reload
- `kb_server/embed_client.py` — Embedding client
- `kb_server/vector_store.py` — Vector store abstraction
- `kb_server/retrieval/` — Retrieval pipeline (hybrid search, reranker)
- `ingest/` — Ingestion pipeline (parsers, registry, classifiers, workers)
- `ingest/core/cron.py` — Cron matcher
- `ingest/job/` — Job manager
- `kb_server/schedules/` — Schedule management router
- `kb_server/health_server.py` — Health check endpoints
- `kb_server/telemetry/` — Prometheus metrics
- `tests/` — Test suite

### Config & Env
- `.env` — Environment configuration
- `config/.env.local` — Local config example
- `kb_server/config/loader.py` — ConfigLoader implementation
- `kb_server/config/router.py` — Config REST API

### Docs
- `.planning/REQUIREMENTS.md` — All requirement definitions
- `.planning/phases/28c-admin-spa-panel/` — Admin SPA phase artifacts
- `.planning/phases/52-ingestion-schedule/` — Schedule management artifacts

## Success Criteria

1. BugBash finds and fixes all P0/P1 bugs; remaining P2 bugs tracked
2. E2E test suite passes (auth, admin panel, schedules)
3. Security audit produces report with 0 critical/high findings
4. All v0.1.5 features documented in README and OPERATIONS docs
5. Top-3 performance bottlenecks identified and resolved

---

*Phase: 53-quality-polish*
*Context gathered: 2026-06-29*
