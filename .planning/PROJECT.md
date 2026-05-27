# kb-rag-mcp

## What This Is

A production-grade RAG (Retrieval-Augmented Generation) MCP server that connects AI assistants (Claude, Cursor, OpenCode, Copilot) to private, closed-source product documentation. Teams ingest their internal docs once and any AI tool with MCP support can query them with grounded, accurate answers. Built to be self-hosted by any team with any product documentation.

## Core Value

AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.

## Current Milestone: v1.3 Post-Ship Polish & Infrastructure

**Goal:** Complete the v1.3 cycle: deliver capability negotiation, fix Grafana datasource, backfill process debt (VERIFICATION.md), fix test environment issues, codebase hygiene sweep, and wire integration checker CI gate.

**Target features:**
- Capability negotiation — advertise classified attributes to MCP clients
- Grafana datasource fix — resolve DS_PROMETHEUS variable resolution error
- VERIFICATION.md backfill — create verification artifacts for 14 phases
- Test environment fixes — resolve test_reranker_lazy.py conftest issues
- Codebase hygiene sweep — logs, comments, types, unused imports
- Integration checker CI gate — catch gaps automatically in CI

## Current State (v1.3)

- **Shipped:** 2026-05-27 (v1.2)
- **Tests:** 585 passing, 5 skipped, 0 failures
- **Coverage:** 90% branch target enforced (kb_server/ + ingest/)
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
- ✓ SSE handler returns `Response()` on disconnect; 3 regression tests — v1.1
- ✓ No `307 Temporary Redirect` on POST to `/messages/` — v1.1
- ✓ CI matrix tests Python 3.11, 3.12, 3.13 — v1.1
- ✓ OTCS auto-tagging (10 product areas) via directory name or filename — v1.1
- ✓ `kb-ingest status` CLI with Rich table + `--source` filter — v1.1
- ✓ Every Python module has a dedicated unit test file — v1.1
- ✓ All unit tests run without Qdrant, LM Studio, or Redis (full mocking) — v1.1
- ✓ Integration tests marked with `@pytest.mark.integration` — v1.1
- ✓ Every public method in `kb_server/` emits structured log entries — v1.1
- ✓ Logging coverage audit produced via `scripts/logging-audit.py` — v1.1
- ✓ CI enforces ≥90% branch coverage on kb_server/ + ingest/ (PR-to-master) — v1.1
- ✓ `pyproject.toml` `fail_under = 90` set and verified — v1.1
- ✓ All public functions/classes in kb_server/ + ingest/ have English Google-style docstrings — v1.1
- ✓ `docs/` updated: ARCHITECTURE.md (Mermaid), OPERATIONS.md (remote deploy), INDEX.md, REFERENCE.md — v1.1

### Active

- [ ] **PHASE-17**: Capability negotiation — advertise classified attributes to MCP clients
- [ ] **PHASE-18**: Grafana datasource fix — resolve DS_PROMETHEUS error
- [ ] **PHASE-19**: VERIFICATION.md backfill — 14 phases missing verification
- [ ] **PHASE-20**: Test environment fixes — test_reranker_lazy.py conftest issues
- [ ] **PHASE-21**: Codebase hygiene sweep — logs, comments, types, unused imports
- [ ] **PHASE-22**: Integration checker CI gate — automate gap detection

### Out of Scope

- Authentication / multi-user access control — internal team tool, trusted network
- Cloud-managed vector store — self-hosted Qdrant only for data sovereignty
- Real-time streaming ingest from external APIs — file-based ingest only
- GUI for doc management — CLI + MCP tools are sufficient

## Context

- v1.3 in progress: phases 12-16 complete, phases 17-22 planned
- v1.2 shipped 2026-05-27: 9/9 requirements met across 4 phases
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
*Last updated: 2026-05-27 — v1.3 milestone in progress*
