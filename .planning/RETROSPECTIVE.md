# Retrospective

---

## Milestone: v0.1.0 — Release-Readiness

**Shipped:** 2026-05-19
**Phases:** 4 | **Plans:** 13

### What Was Built

1. Deleted legacy `server/` module — `kb_server/` is now the single canonical package
2. Real BM25+dense RRF hybrid search — the sparse path was effectively dead code before
3. Single `bootstrap_env()` entry point replacing 6+ copy-pasted `load_dotenv` blocks
4. File-watcher deletion removes stale Qdrant vectors when source files are deleted
5. Secrets removed from git tracking; `CONTRIBUTING.md` with `git-filter-repo` remediation guide
6. 88% branch coverage on `kb_server/` (up from ~50%); 491 passing tests, 0 failures
7. GitHub Actions CI on every push/PR; integration tests for ingest→search and routing
8. Multi-stage Dockerfile + `scripts/quickstart.sh` + rewritten README getting-started guide

### What Worked

- **Coarse phase granularity:** 4 phases at milestone scope let each phase ship independently testable value without excessive planning overhead
- **Test-first approach on coverage gaps:** Writing targeted unit tests per module (cache, server tools, embed, reranker) was more efficient than trying to raise coverage globally
- **Parallel problem identification:** Finding all 19 pre-existing test failures upfront, categorizing by root cause, and batching fixes prevented rework
- **Archived planning artifacts:** Keeping ROADMAP/REQUIREMENTS as lean living documents and archiving per milestone kept context cost constant

### What Was Inefficient

- **`sys.modules` stub pollution:** `test_vector_store_unit.py` replacing qdrant_client models caused downstream tests to see MagicMock enums. Should have been isolated with `monkeypatch` or module-scoped cleanup from the start
- **MCP server coverage:** `server.py` ended at 78% — the tool handler dispatch paths are hard to unit-test without a running MCP context; should have set up a lightweight MCP test harness earlier
- **Rich markup fixes required manual inspection:** The `[/{variable}]` → `[/]` pattern and missing `f`-prefix on strings were not caught by linting; `flake8` doesn't cover rich markup

### Patterns Established

- `getattr(x, 'value', x) == 'keyword'` pattern for comparing Pydantic/enum values when `sys.modules` stubs are present
- Phase summaries in `.planning/phases/*/` as the authoritative record of what was done
- `bootstrap_env()` called exactly once at each entry point (`if __name__ == "__main__"` or CLI `main()`)
- Docker Compose `depends_on: condition: service_healthy` for Qdrant readiness

### Key Lessons

1. **Stub at the lowest level possible** — patching `sys.modules` at import time affects all downstream module imports; prefer `unittest.mock.patch` with explicit targets
2. **Set test baseline explicitly** — documenting "19 pre-existing failures" before starting prevented false regressions during the fix cycle
3. **Coverage thresholds belong in CI, not just local runs** — `--cov-fail-under=80` in CI enforces the constraint automatically
4. **Quickstart scripts need a clean-machine test** — the `quickstart.sh` is validated by inspection only; a Docker-based clean-room test would catch env assumptions

### Cost Observations

- Sessions: ~8 across 5 days
- Model: claude-sonnet-4.6 throughout
- Most expensive sessions: Phase 3 coverage push (large test file generation)
- Notable: Phase 4 was effectively free — artifacts pre-existed from prior work; mostly orchestration

---

## Milestone: v0.1.5 — Streamable HTTP & Management Platform

**Shipped:** 2026-06-29
**Phases:** 18 | **Plans:** 28

### What Was Built

1. **Streamable HTTP transport** — browser-compatible MCP over GET/POST/DELETE/OPTIONS on `/mcp` with session lifecycle (idle timeout, count limit, background sweep), CORS, auth middleware, and Prometheus metrics
2. **Auth & User Management API** — SQLAlchemy models (User, ApiKey, AuditLog, ErasureRequest), CRUD REST endpoints, JWT session cookies, RBAC, GDPR erasure workflow, session management UI
3. **Admin SPA Panel** — Alpine.js+HTMX+Bootstrap 5 tabbed UI at `/admin/` with login modal, role gating, 6 tabs (Documents, Monitoring, Ingestion, Admin, Profile, Query Analytics), advanced filters, CSV/JSON export, chunk preview, document tag editor, schedule manager
4. **Observability & Config Infrastructure** — request ID middleware, percentile latency metrics (p50/p95/p99), Grafana dashboard embedding with time range selector, SQLite config table with hot-reload, provider aliases
5. **Ingestion Schedule Management** — pure Python 5-field cron matcher, CRUD API at `/api/v1/schedules`, background asyncio loop (30s), Admin UI Schedule tab
6. **Quality Polish** — 14 E2E tests covering auth/admin/schedule flows, security audit (login rate limiting, startup warnings), performance optimization (croniter O(1) matching, joinedload single-query JOIN, ConfigLoader TTL cache), documentation (API.md, README, OPERATIONS updates)

### What Worked

- **Structured phase planning with wave parallelization** — 18 phases across multiple concurrent workstreams (transport, auth, SPA, observability, config, schedules) shipped efficiently
- **UAT-driven gap closure** — Phase 28c-fixes used UAT results to systematically fix 13+ issues across the Admin SPA, ensuring production readiness
- **Security audit as separate workstream** — systematic review found and documented all findings; rate limiting and startup warnings were quick wins
- **Performance profiling targeted at O(n)→O(1) transformations** — replacing brute-force cron scanning with croniter and N+1 queries with joinedload gave immediate, measurable improvements
- **Milestone audit** — pre-close audit with artifact scanning caught a stale quick task that was easily resolved

### What Was Inefficient

- **Cross-phase auth dependencies** — auth system evolved across 4+ phases (28b base, 28c SPA integration, 44 hardening, 53 rate limiting), causing rework and test isolation churn
- **E2E test setup overhead** — required running server with auth enabled, monkeypatching AUTH_ENABLED at the right level, and handling session cookie lifecycle across test functions
- **gsd-tools artifact audit limitations** — quick task status detection tool flagged a completed task as "unknown" because it relied on file metadata not present in the quick task directory

### Patterns Established

- `monkeypatch.setattr("module.attribute", value)` for env-var-like configuration in tests (more reliable than os.environ manipulation when modules cache at import time)
- In-memory rate limiter (token bucket per subject with sliding window) — sufficient for internal tool, documented as lost-on-restart
- ConfigLoader TTL cache (1s default) as thread-safe alternative to persistent connections
- Cron matching: `croniter` for O(1) evaluation + `validate_cron()` pre-check for backward-compatible error behavior

### Key Lessons

1. **Auth should be designed once, not iterated** — auth is a cross-cutting concern that touches every subsystem; getting it right (or close to right) in the first phase saves significant rework across 5+ downstream phases
2. **Artifact audit before closing** — the pre-close audit caught a quick task that was implemented but never marked verified; adding audit to the close workflow prevents forgotten items
3. **Performance wins come from algorithmic improvements, not micro-optimizations** — replacing O(n) with O(1) in two hot paths (cron matching, DB queries) was far more impactful than any code-level micro-optimization
4. **Internal tool security is about awareness, not perfection** — documenting accepted risks (stdio no-auth, default admin password) with startup warnings and operational guidance is the right approach for a self-hosted internal tool

### Cost Observations

- Total sessions: ~25+ across 14 days
- Heavy sessions: Phase 53 multi-workstream quality polish (bug bash, E2E tests, security audit, perf tuning)
- Notable: Phase 28c Admin SPA was the most complex phase — Alpine.js+HTMX SPA with CSP, auth integration across 6 tabs, responsive sidebar, and UAT-driven gap closure

---

## Cross-Milestone Trends

| Milestone | Phases | Tests | Coverage | Duration |
|-----------|--------|-------|----------|----------|
| v0.1.0 | 4 | 491 | 88% | 5 days |
| v0.1.5 | 18 | 1541 | 90% | 14 days |
