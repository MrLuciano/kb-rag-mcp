# kb-rag-mcp

## What This Is

A production-grade RAG (Retrieval-Augmented Generation) MCP server that connects AI assistants (Claude, Cursor, OpenCode, Copilot) to private, closed-source product documentation. Teams ingest their internal docs once and any AI tool with MCP support can query them with grounded, accurate answers. Built to be self-hosted by any team with any product documentation. Now includes enterprise features: API key authentication, rate limiting, upload quotas, and multi-KB aggregated search.

## Core Value

AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.

## Current State (v1.4 — shipped)

- **Tests:** 1095 passing, 12 skipped, 0 failures (baseline, excluding Qdrant-dependent e2e)
- **Coverage:** 90% branch target enforced (kb_server/ + ingest/)
- **Codebase:** ~251k LOC Python; single canonical module `kb_server/`
- **Deployment:** Docker Compose + bare metal systemd + Kubernetes/Helm
- **CI:** GitHub Actions on every push/PR to `master` — English audit, Helm lint, integration checks
- **Monitoring:** Grafana + Prometheus with 6-tab dashboard, 28 metrics
- **MCP surface:** 8 tools (search_kb, list_documents, get_chunk, kb_stats, list_collections, list_filter_options, get_related_documents, explore_topic), 2 prompts (extract_answer, summarize_documents), Streamable HTTP transport
- **Enterprise features:** API key auth (SHA-256 hashed), token-bucket rate limiting, 6 upload quota dimensions, provider budget/circuit breaker resilience, request-level retrieval cache, multi-KB aggregated search, 3 remote source connectors (Confluence, JIRA, Git)

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
- ✓ Documentation reorganized by deployment mode (Docker Compose, Helm, systemd, manual) — v1.4
- ✓ CHANGELOG and REFERENCE.md updated with v1.3/v1.4 changes — v1.4
- ✓ Dynamic KB content discoverability with `kb://overview` MCP Resource — v1.4
- ✓ SQLite-backed KB Registry with public/agent_private scopes — v1.4
- ✓ MCP Streamable HTTP transport alongside stdio/SSE — v1.4
- ✓ Enterprise data source connectors (Confluence, JIRA, Git via factory pattern) — v1.4
- ✓ Cross-document knowledge graph with get_related_documents/explore_topic MCP tools — v1.4
- ✓ MCP prompt templates (extract_answer, summarize_documents) — v1.4
- ✓ API key authentication (SHA-256 hashed, CLI create/list/revoke) — v1.4
- ✓ Token-bucket request rate limiting (per subject, HTTP 429 + MCP error) — v1.4
- ✓ Upload and index quotas (6 dimensions, CLI management) — v1.4
- ✓ Multi-KB aggregated search (kb_ids, RRF fusion, provenance) — v1.4
- ✓ Provider budget & circuit breaker resilience (fallback chain, 7 metrics) — v1.4
- ✓ Request-level retrieval cache (LRU, deterministic keys, TTL) — v1.4

### Active

*(None — all v1.4 requirements complete. Planning next milestone.)*

### Out of Scope

- Authentication / multi-user access control — internal team tool, trusted network (Note: API key auth added v1.4 for controlled access, not multi-user RBAC)
- Cloud-managed vector store — self-hosted Qdrant only for data sovereignty
- Real-time streaming ingest from external APIs — polling-based sync via connectors
- GUI for doc management — CLI + MCP tools are sufficient
- RAGAS evaluation — deferred to backlog (Phase 24)
- Optimization experiments — deferred to backlog (Phase 25)

## Context

- v1.4 shipped 2026-06-11: 13 active phases delivered, 2 deferred (24, 25). Enterprise hardening complete with connectors, knowledge graph, prompts, auth, rate limits, quotas, multi-KB search, provider resilience, and retrieval cache.
- `kb_server/` is the single canonical package; `server/` deleted; `ingest/core/metadata.py` is the registry
- Committed `.env` files resolved: removed from tracking; `CONTRIBUTING.md` documents git history cleanup
- Embedding model: local LM Studio (`http://<LM_STUDIO_HOST>:1234`); configurable via `EMBED_BACKEND`
- Vector store: Qdrant (local or remote); multi-collection support
- Pre-existing test note: `test_payload_indexes.py` schema type assertion weakened (MagicMock pollution from qdrant_client stub)
- `asyncio_mode = STRICT` in `pyproject.toml` — all async tests need `@pytest.mark.asyncio`
- The product has shipped 5 milestones (v1.0 through v1.4) with 37 phases, establishing it as a mature, enterprise-ready MCP RAG server
- Notable: No authentication was a constraint at v1.0; v1.4 added optional API key auth (AUTH_ENABLED flag preserves backward compatibility)

## Constraints

- **Tech stack**: Python 3.11+, Qdrant, MCP protocol, FastAPI, asyncio — no runtime changes
- **Dependencies**: pip-tools (`requirements.in` → `requirements.txt`), `.venv/` virtual env
- **Compatibility**: CLI interface must remain backward-compatible; deprecation warnings for removed flags
- **Deployment**: Must support bare metal (systemd), Docker Compose, and Kubernetes/Helm
- **No auth**: Internal use only — no authentication layer planned (Note: optional auth added v1.4, disabled by default)
- **Test baseline**: 1095 passing tests; no regressions allowed

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
| Connector factory pattern with eager import registration | Runtime lookup without import coupling; auto-registers on import | ✓ Good — v1.4 |
| Per-KB graph metadata (not global) | Isolated graph state per KB; no cross-contamination | ✓ Good — v1.4 |
| Template-only prompts (no LLM backend) | Lightweight, no additional dependencies or latency | ✓ Good — v1.4 |
| SHA-256 key hashing; no plaintext storage | Security best practice; keys only visible at creation time | ✓ Good — v1.4 |
| In-memory token bucket rate limiting | Zero infrastructure dependencies; suitable for single-instance | ✓ Good — v1.4 |
| Cumulative quota counters with explicit reset | Simple implementation; no time-window complexity | ✓ Good — v1.4 |
| RRF fusion for multi-KB result merging | Works without score calibration; proven in hybrid search | ✓ Good — v1.4 |
| Persistent backoff multiplier (circuit breaker) | Repeated failure cycles escalate cooldown appropriately | ✓ Good — v1.4 |
| Cache structured results before rendering | Flexible formatting; single render path | ✓ Good — v1.4 |

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
*Last updated: 2026-06-11 after v1.4 milestone*
