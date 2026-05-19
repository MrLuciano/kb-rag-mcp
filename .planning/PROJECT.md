# kb-rag-mcp

## What This Is

A production-grade RAG (Retrieval-Augmented Generation) MCP server that connects AI assistants (Claude, Cursor, OpenCode, Copilot) to private, closed-source product documentation. Teams ingest their internal docs once and any AI tool with MCP support can query them with grounded, accurate answers. Built to be self-hosted by any team with any product documentation.

## Core Value

AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.

## Requirements

### Validated

- ✓ Semantic search over ingested documents (dense vector search via Qdrant) — existing
- ✓ MCP server exposing `search_kb`, `list_documents`, `get_chunk`, `kb_stats` tools — existing
- ✓ Async ingest pipeline (PDF, markdown, text) with metadata extraction — existing
- ✓ Hybrid search (dense + sparse BM25 RRF fusion) — implemented (FASE 12)
- ✓ Cross-encoder reranking — implemented (FASE 12)
- ✓ Multi-collection routing via `CollectionRouter` and `CollectionManager` — existing
- ✓ Product/version metadata filtering — existing
- ✓ Query logging and analytics — existing
- ✓ LRU + optional Redis caching — existing
- ✓ Batch ingest with job tracking and progress reporting — existing
- ✓ File watcher for automatic re-ingest on doc changes — existing
- ✓ Migration tooling (export/import/validate) — existing (FASE 1.5)
- ✓ Grafana observability dashboard — existing (FASE 9)
- ✓ Kubernetes/Helm deployment — existing (FASE 10)
- ✓ Security hardening documentation — existing
- ✓ RAG evaluation framework (golden dataset, hit rate, MRR) — existing (FASE 16)

### Active

- [ ] Eliminate duplicate `server/` vs `kb_server/` module split — consolidate to `kb_server/` only
- [ ] Fix hybrid search fallback bug — sparse search path is effectively dead code
- [ ] Implement file watcher deletion — stale docs survive in Qdrant after source file removal
- [ ] Fix batch ingest checksum placeholder — deduplication broken for batch runs
- [ ] Remove committed `.env` files from git tracking, add to `.gitignore`
- [ ] Raise test coverage on critical integration paths (target ≥ 80% on `kb_server/`)
- [ ] Docker Compose deployment path (currently bare metal + K8s only)
- [ ] Single `bootstrap_env()` entry point — eliminate 6+ copy-pasted `load_dotenv` blocks
- [ ] README and docs reflect all 16 features accurately
- [ ] `config/.env.template` as canonical example — no real values in tracked files

### Out of Scope

- Authentication / multi-user access control — internal team tool, trusted network
- Cloud-managed vector store — self-hosted Qdrant only for data sovereignty
- Real-time streaming ingest from external APIs — file-based ingest only
- GUI for doc management — CLI + MCP tools are sufficient

## Context

- 16 features implemented across FASE 1–16 lifecycle; all passing tests at last baseline (268 pass, 19 pre-existing failures requiring live services)
- Dual module layout (`server/` legacy, `kb_server/` canonical) is the biggest structural debt — `server/` should be deleted
- Committed `.env` files need to be removed from git history before any public release
- Embedding model: local LM Studio (`http://<LM_STUDIO_HOST>:1234`); configurable
- Vector store: Qdrant (local or remote); multi-collection support in `kb_server/`
- Pre-existing test failures: `test_reranker.py` (model download required), `test_payload_indexes.py` (live Qdrant + data required) — not regressions

## Constraints

- **Tech stack**: Python 3.11+, Qdrant, MCP protocol, FastAPI, asyncio — no runtime changes
- **Dependencies**: pip-tools (`requirements.in` → `requirements.txt`), `.venv/` virtual env
- **Compatibility**: CLI interface must remain backward-compatible; deprecation warnings for removed flags
- **Deployment**: Must support bare metal (systemd), Docker Compose, and Kubernetes/Helm
- **No auth**: Internal use only — no authentication layer planned
- **Test baseline**: 268 passing tests; no regressions allowed

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| `kb_server/` is canonical, `server/` is legacy | Avoid confusion; new features only in `kb_server/` | — Pending (delete `server/` in cleanup phase) |
| Local embedding model (LM Studio) | Data sovereignty for closed-source doc content | ✓ Good |
| Qdrant for vector store | Production-grade, self-hostable, multi-collection support | ✓ Good |
| MCP protocol for AI tool integration | Standard protocol; works with Claude, Cursor, OpenCode, Copilot | ✓ Good |
| Generic product names in codebase (AppServer/DataSync/AdminPortal) | Enable open-source release without exposing client details | ✓ Good |
| `.env` files committed (historical) | Must be removed from git history before public release | ⚠️ Revisit |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-19 after initialization*
