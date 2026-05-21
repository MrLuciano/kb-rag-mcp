# kb-rag-mcp

## What This Is

A production-grade RAG (Retrieval-Augmented Generation) MCP server that connects AI assistants (Claude, Cursor, OpenCode, Copilot) to private, closed-source product documentation. Teams ingest their internal docs once and any AI tool with MCP support can query them with grounded, accurate answers. Built to be self-hosted by any team with any product documentation.

## Core Value

AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.

## Current Milestone: v1.1 Quality & Operational Excellence

**Goal:** Harden the server for real-world remote deployment, expand test coverage with proper isolation mocking, and enforce a quality gate.

**Target features:**
- SSE stability fix + regression tests (handle_sse NoneType crash on starlette 1.0.0)
- Python 3.13 compatibility — CI matrix + any 3.11-only constructs fixed
- OTCS-specific doc tagging — auto-tag ingested docs by product area
- Ingest status / health CLI — `kb-ingest status` with last run, doc count, errors
- Unit tests for all Python source with mocks for Qdrant, LM Studio, all external deps
- Logging coverage — all methods logged; structured log coverage audit
- Quality gate — coverage threshold enforced in CI; target ≥90% branch on `kb_server/`
- Documentation improvements — inline docstrings, architecture, operational runbook

## Current State (v1.0)

- **Shipped:** 2026-05-19
- **Tests:** 491 passing, 5 skipped, 0 failures
- **Coverage:** 88% branch on `kb_server/`
- **Codebase:** ~251k LOC Python; single canonical module `kb_server/`
- **Deployment:** Docker Compose + bare metal systemd + Kubernetes/Helm
- **CI:** GitHub Actions on every push/PR to `master`

## Requirements

### Validated

- ✓ Semantic search over ingested documents (dense vector search via Qdrant) — existing
- ✓ MCP server exposing `search_kb`, `list_documents`, `get_chunk`, `kb_stats` tools — existing
- ✓ Async ingest pipeline (PDF, markdown, text) with metadata extraction — existing
- ✓ Hybrid search (dense + sparse BM25 RRF fusion) — validated v1.0
- ✓ Cross-encoder reranking — existing (FASE 12)
- ✓ Multi-collection routing via `CollectionRouter` and `CollectionManager` — validated v1.0
- ✓ Product/version metadata filtering — existing
- ✓ Query logging and analytics — existing
- ✓ LRU + optional Redis caching — existing
- ✓ Batch ingest with job tracking and progress reporting — existing
- ✓ File watcher for automatic re-ingest on doc changes — existing
- ✓ Migration tooling (export/import/validate) — existing
- ✓ Grafana observability dashboard — existing
- ✓ Kubernetes/Helm deployment — existing
- ✓ Security hardening documentation — existing
- ✓ RAG evaluation framework (golden dataset, hit rate, MRR) — existing
- ✓ Single `kb_server/` canonical module; `server/` legacy deleted — v1.0
- ✓ Real SHA-256 batch deduplication — v1.0
- ✓ Single `bootstrap_env()` entry point — v1.0
- ✓ File watcher deletion removes stale Qdrant vectors — v1.0
- ✓ Secrets removed from git tracking; `config/.env.template` only — v1.0
- ✓ `CONTRIBUTING.md` with secret remediation guide — v1.0
- ✓ ≥80% branch coverage on `kb_server/` (achieved 88%) — v1.0
- ✓ Integration tests: ingest → search_kb → verify; multi-collection routing — v1.0
- ✓ GitHub Actions CI on push/PR to master — v1.0
- ✓ Multi-stage Dockerfile (builder + slim runtime) — v1.0
- ✓ `scripts/quickstart.sh` one-command setup — v1.0
- ✓ README end-to-end getting-started guide — v1.0

### Active

- [ ] **SSE-01**: SSE `handle_sse` returns `Response()` on disconnect; regression test covers starlette 1.0.0 + Python 3.13
- [ ] **SSE-02**: No `307 Temporary Redirect` loop on POST to `/messages/`; trailing-slash consistency verified
- [ ] **COMPAT-01**: All CI jobs run on Python 3.11 and Python 3.13 without failures
- [ ] **COMPAT-02**: No Python 3.11-only syntax constructs remain that break on 3.13
- [ ] **INGEST-01**: Ingested OTCS docs are auto-tagged by product area (WebReports, xECM, Workflow, etc.) without manual `--product` flag
- [ ] **INGEST-02**: `kb-ingest status` command shows last ingest time, total docs, total chunks, error count per source
- [ ] **TEST-01**: Every Python module in `kb_server/` and `ingest/` has a corresponding unit test file
- [ ] **TEST-02**: All unit tests run without requiring Qdrant, LM Studio, or Redis — external deps fully mocked
- [ ] **TEST-03**: Integration tests remain separate and clearly marked; can be skipped with `pytest -m "not integration"`
- [ ] **LOG-01**: Every public method in `kb_server/` emits at least one structured log entry at appropriate level
- [ ] **LOG-02**: Log coverage audit report produced; gaps resolved
- [ ] **QUAL-01**: CI enforces ≥90% branch coverage on `kb_server/`; build fails on regression
- [ ] **QUAL-02**: `pyproject.toml` `[tool.coverage.report]` `fail_under = 90` set and tested
- [ ] **DOC-01**: All public functions and classes in `kb_server/` and `ingest/` have English docstrings
- [ ] **DOC-02**: `docs/` folder updated to reflect v1.1 changes (architecture, ingest workflow, remote deploy)

### Out of Scope

- Authentication / multi-user access control — internal team tool, trusted network
- Cloud-managed vector store — self-hosted Qdrant only for data sovereignty
- Real-time streaming ingest from external APIs — file-based ingest only
- GUI for doc management — CLI + MCP tools are sufficient

## Context

- v1.0 shipped 2026-05-19: all 15 release-readiness requirements met across 4 phases
- `kb_server/` is the single canonical package; `server/` deleted; `ingest/core/metadata.py` is the registry
- Committed `.env` files resolved: removed from tracking; `CONTRIBUTING.md` documents git history cleanup
- Embedding model: local LM Studio (`http://<LM_STUDIO_HOST>:1234`); configurable via `EMBED_BACKEND`
- Vector store: Qdrant (local or remote); multi-collection support
- Pre-existing test note: `test_payload_indexes.py` schema type assertion weakened (MagicMock pollution from qdrant_client stub)
- `asyncio_mode = STRICT` in `pyproject.toml` — all async tests need `@pytest.mark.asyncio`

## Constraints

- **Tech stack**: Python 3.11+, Qdrant, MCP protocol, FastAPI, asyncio — no runtime changes
- **Dependencies**: pip-tools (`requirements.in` → `requirements.txt`), `.venv/` virtual env
- **Compatibility**: CLI interface must remain backward-compatible; deprecation warnings for removed flags
- **Deployment**: Must support bare metal (systemd), Docker Compose, and Kubernetes/Helm
- **No auth**: Internal use only — no authentication layer planned
- **Test baseline**: 491 passing tests; no regressions allowed

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| `kb_server/` is canonical, `server/` deleted | Single source of truth; avoid import confusion | ✓ Good — v1.0 |
| Local embedding model (LM Studio/Ollama) | Data sovereignty for closed-source doc content | ✓ Good |
| Qdrant for vector store | Production-grade, self-hostable, multi-collection support | ✓ Good |
| MCP protocol for AI tool integration | Standard protocol; works with Claude, Cursor, OpenCode, Copilot | ✓ Good |
| Generic product names in codebase | Enable open-source release without exposing client details | ✓ Good |
| `asyncio_mode = STRICT` in pyproject.toml | Enforce explicit async test marking; prevents silent sync execution | ✓ Good |
| `bootstrap_env()` single entry point | Eliminate 6+ copy-pasted `load_dotenv` blocks | ✓ Good — v1.0 |
| fastembed BM25 for sparse vectors | No separate sparse model server needed; embedded in process | ✓ Good |
| Weaken `PayloadSchemaType` enum assertion in test | MagicMock pollution across test suite; assertion redundant | — Acceptable tech debt |

## Evolution

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-21 — v1.1 milestone started*
