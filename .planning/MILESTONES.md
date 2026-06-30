# Milestones

## 0.1.5 Streamable HTTP & Management Platform (Shipped: 2026-06-30)

**Phases completed:** 19 phases, 28 plans, 23 tasks

**Key accomplishments:**

- Session limit enforcement via _SessionTracker with oldest-idle eviction, Prometheus active-session/eviction metrics, and 60-second background sweep task.
- [x-cloak] CSS rule, htmx:afterSettle Alpine.initTree handler, session-cookie auth refactor, and CSP-compatible toggle method to unblock Admin UI user creation
- Fix admin login overlay not appearing — `@alpinejs/csp` silently rejected `x-data="adminApp()"` (global function calls unsupported in CSP build).
- Config system wired into production server: health server mounts REST API, server.py replaces os.getenv with ConfigLoader.get(), and hot-reload callbacks log runtime config changes
- COMPLETE
- COMPLETE
- Implementation: Cron matcher, schedule CRUD, API router, background scheduler, Admin UI.
- 2026-06-29

---

## v0.1.0 — Release-Readiness

**Shipped:** 2026-05-19
**Phases:** 4 | **Plans:** 13 | **Tests:** 491 passing

### Delivered

Made kb-rag-mcp safe to release publicly: deleted legacy `server/` module, fixed real BM25 hybrid search, unified env loading, hardened data integrity (file-watcher deletion, secrets), raised test coverage to 88% branch with full CI, and shipped Dockerfile + quickstart.sh + new README getting-started guide.

### Key Accomplishments

1. `kb_server/` is now the single canonical module — `server/` and `ingest/registry.py` deleted
2. Real BM25+dense RRF hybrid search — sparse path was dead code before this milestone
3. 491 tests passing, 88% branch coverage on `kb_server/` (up from ~50% pre-milestone)
4. GitHub Actions CI on every push/PR; integration tests cover ingest→search and multi-collection routing
5. Multi-stage Dockerfile + `scripts/quickstart.sh` — zero-to-running setup in one command
6. Secrets fully removed from git tracking; `CONTRIBUTING.md` documents remediation for teams

### Stats

- Timeline: 2026-05-14 → 2026-05-19 (5 days)
- Files changed: 308 | Python LOC: ~251k | Commits: 103
- Requirements: 15/15 v1 requirements met

### Git Tag

`v0.1.0`

---

## v0.1.2 — Tech Debt & Classification

**Shipped:** 2026-05-27
**Phases:** 4 (9, 10, 11, 11.1) | **Plans:** 9 | **Tests:** 585 passing

### Delivered

Established operational reliability and auto-classification maturity: lazy cross-encoder loading (~500MB saved, ~10s faster startup), pre-flight health checks with non-fatal warnings, Helm lint CI gate, MagicMock pollution resolved in test suite (3 files), logging coverage CI enforcement (40% threshold), auto-classification of documents with Vendor/Product/Subsystem/Version attributes, metadata gap-filling from PDF/DOCX, and vendor/subsystem fields made visible and filterable in search results.

### Key Accomplishments

1. **Startup reliability** — Cross-encoder loads lazily on first `rerank()` call (4 regression tests); pre-flight health checks warn on unreachable Qdrant/LM Studio without crashing; `kb-ingest check health` CLI with Rich table output; 4 embedding backends documented (lmstudio-sdk, lmstudio-rest, ollama, openai-compat)
2. **CI quality gates** — `helm lint --strict` runs on every push; real qdrant_client imports replace 100+ lines of MagicMock stubs; logging audit enforced at 40% threshold on PR-to-master
3. **Auto-classification** — Vendor inference (15 products mapped to OpenText), subsystem inference (8 functional categories), document metadata extraction (PDF/DOCX), gap-filling enrichment, all backward-compatible with existing OTCS tagging
4. **Vendor/subsystem search integration** — Fields extracted in search results, filterable via MCP tools, visible in list_documents output — completed via Phase 11.1 after milestone audit discovered the gap

### Stats

- Timeline: 2026-05-14 → 2026-05-27 (13 days, including Phase 11.1 remediation)
- Files changed: 30 | Commits: 19 feature commits
- Requirements: 9/9 v0.1.2 requirements met
- Phase 11.1 was a decimal-phase insertion to remediate critical integration gap found by milestone audit

### Git Tag

`v0.1.2`

---

## v0.1.1 — Quality & Operational Excellence

**Shipped:** 2026-05-23
**Phases:** 4 (5-8) | **Plans:** 10 | **Tests:** 576 passing

### Delivered

Established operational maturity and code quality foundations: SSE stability with Python 3.13 support, full test isolation from external services, 90% branch coverage enforcement on PR-to-master, OTCS product auto-tagging for 10 OpenText products, and English-only codebase with comprehensive Google-style docstrings.

### Key Accomplishments

1. **SSE stability & Python 3.13 support** — Fixed NoneType crash in SSE handler, pinned Starlette ≥1.0.0, added CI matrix testing across Python 3.11/3.12/3.13
2. **Full test isolation** — Added 3 session-scoped mock fixtures (Qdrant, embed client, Redis) enabling `pytest -m "not integration"` to run without external services; 518 unit tests pass without infrastructure
3. **90% coverage enforcement** — Set `fail_under = 90` in pyproject.toml and CI, enforcing branch coverage on PR-to-master for both kb_server/ and ingest/
4. **OTCS product auto-tagging** — Added 18 directory aliases and 10 filename patterns enabling auto-detection of 10 OpenText product areas (ContentServer, WebReports, xECM, Workflow, CSIDE, Brava, OT2, DocumentViewer, APIGateway, ArchiveCenter)
5. **CLI status command** — Added `kb-ingest status` with Rich table output showing per-source file/chunk/error counts, with optional `--source` filtering
6. **English-only codebase** — Fixed 105 docstring gaps (32 missing + 73 Portuguese → English), verified with AST-based audit script; all public methods now have Google-style docstrings

### Stats

- Timeline: 2026-05-14 → 2026-05-23 (8 days)
- Files changed: 75 | +4,980 insertions, -3,106 deletions | Python LOC: 13,457
- Requirements: 15/15 v0.1.1 requirements met
- Commits: 16 feature commits

### Git Tag

`v0.1.1`

---

## v0.1.3 — Post-Ship Polish & Infrastructure

**Shipped:** 2026-05-27
**Phases:** 11 (12-22) | **Plans:** 27 | **Tests:** 656 passing

### Delivered

English-only codebase with CI enforcement, multilingual README (EN/PT-BR/ES), Grafana + Prometheus monitoring stack (6 tabs, 28 panels, 4 services), PowerShell Windows firewall config, document reclassification engine (in-place metadata + SQLite rollback), capability negotiation (FilterTermsCache + list_filter_options), Grafana datasource fix (stable UID), 13 VERIFICATION.md files + gap detection, LOG_PATH PermissionError fix, codebase hygiene sweep (13 unused imports, 3 TODOs, 2 dead code), and integration checker CI gate (3 checks, needs: test).

### Key Accomplishments

1. **English-only codebase** — All Portuguese translated to English across ~35 files in `kb_server/` and `ingest/`; CI gate with `english-audit --check-inline --fail-under 0` on every push/PR; false positive technical terms removed from detection set
2. **Grafana + Prometheus monitoring** — `/metrics` endpoint at port 8080 exposing 28 Prometheus metrics; 6-tab Grafana dashboard with 28 panels; 4-service Docker Compose stack (Qdrant, kb-rag-mcp, Prometheus, Grafana); Helm monitoring toggle with StatefulSet + Deployment
3. **Document reclassification** — In-place metadata updates preserve embeddings; SQLite backup/audit tables for rollback; 4 CLI subcommands (run/verify/sessions/rollback) with interactive preview; session-based tracking with 30-day auto-cleanup
4. **Capability negotiation** — MCP server advertises classified attributes (vendor, product, subsystem, version, module) via dynamic tool descriptions; FilterTermsCache with cache-bust marker; `list_filter_options` tool for full enumeration; 33 new tests + integration smoke test
5. **Grafana datasource fix** — Stable `uid: prometheus` resolves dashboard load errors; 63 `${DS_PROMETHEUS}` → `"prometheus"` replacements; `__inputs` sections removed; applied identically across Docker Compose and Helm paths
6. **Process debt resolved** — 13 VERIFICATION.md files backfilled for phases 05-13, 16-18; `scripts/check-verification-gaps.sh` detection script; `scripts/check-integration-gaps.py` wired as CI gate with Rich + JSON output

### Stats

- Timeline: 2026-05-25 → 2026-05-27 (3 days)
- Files changed: 331 | Commits: ~187 feature commits
- Requirements: 26/26 v0.1.3 requirements met (1 cancelled with rationale)
- Final planned milestone — product is feature-complete for target use case

### Git Tag

`v0.1.3`

---

## v0.1.4 — Platform, Analytics & Enterprise

**Shipped:** 2026-06-11
**Phases:** 15 (23-37) | **Plans:** 28 | **Tests:** 1165 passing

### Delivered

Transformed kb-rag-mcp from a single-collection RAG server into a multi-tenant, enterprise-ready platform with streaming HTTP transport, knowledge graph, authentication, rate limiting, quotas, circuit breakers, and retrieval caching.

### Key Accomplishments

1. **Documentation overhaul** — Deployment-mode sections in all docs, two-tier README format (EN/PT-BR/ES), CHANGELOG with per-plan detail
2. **RAGAS Evaluation Pipeline** — 4 custom metrics (faithfulness, answer_relevancy, context_precision, context_recall), CSV/JSON dataset loader, `kb-rag evaluate` CLI, 4 LLM backend wrappers
3. **Optimization Experiments** — Chunking strategies (fixed, recursive, semantic), scoring variants (dense, hybrid, reranked), IR metrics (Recall@K, MRR, NDCG@K), `kb-rag optimize` CLI
4. **Enterprise connectors** — Confluence (Cloud + DC), JIRA, Git connectors with CLI staging and SQLite connector_state
5. **Knowledge Graph** — Cross-document graph metadata (doc_graph_id, entities, topics, related), MCP tools for exploration
6. **Auth & Resilience** — API key authentication, rate limiting, upload quotas, circuit breakers, budget tracking, retrieval cache
7. **Multi-KB Search** — Aggregated search across multiple knowledge bases with RRF fusion and deduplication

### Stats

- Timeline: 2026-05-27 → 2026-06-11 (15 days)
- Files changed: 200+ | Commits: ~150
- Requirements: 59/59 requirements met (many formally tracked in v0.1.5 planning)
- Tech debt: 2 info-severity items (datetime.utcnow() deprecation, missing dedicated multi-KB test file)

### Git Tag

`v0.1.4`
