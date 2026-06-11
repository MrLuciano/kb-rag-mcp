# Retrospective

---

## Milestone: v1.0 — Release-Readiness

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

## Milestone: v1.4 — Platform, Analytics & Enterprise

**Shipped:** 2026-06-11
**Phases:** 13 active (23, 26-37) + 2 deferred (24, 25) | **Plans:** 21

### What Was Built

1. **Documentation overhaul** — Deployment-mode sections in 4 operational docs; CHANGELOG + REFERENCE updated
2. **KB content discoverability** — Dynamic tool descriptions, `kb://overview` MCP Resource
3. **Knowledge Base Registry** — SQLite-backed with public/agent_private scopes, stable kb_<id> names
4. **MCP Streamable HTTP** — `/mcp` HTTP endpoint alongside stdio/SSE
5. **Enterprise connectors** — Confluence, JIRA, Git via factory pattern with incremental sync
6. **Cross-document knowledge graph** — Graph metadata + 2 MCP tools (get_related_documents, explore_topic)
7. **MCP prompt templates** — extract_answer + summarize_documents with prompt discovery
8. **API key authentication** — SHA-256 hashed keys, CLI create/list/revoke, optional via AUTH_ENABLED
9. **Request rate limiting** — Token-bucket per subject, HTTP 429 + MCP error, Prometheus metrics
10. **Upload and index quotas** — 6 dimensions, schema v3→v4, CLI management, pre-enforcement
11. **Multi-KB aggregated search** — kb_ids parameter, RRF fusion, score normalization, dedup
12. **Provider budget & circuit breaker** — State machine, sliding window, fallback chain, 7 metrics
13. **Request-level retrieval cache** — LRU with deterministic keys, TTL, invalidation hooks

### What Worked

- **Phases 29-37 executed efficiently at the tail end** — Connectors through retrieval cache shipped with minimal rework; most phases had single-plans that were completed in one session
- **Two-phase deferral pattern** — Phases 24-25 identified early as lower priority and explicitly deferred, keeping milestone scope focused on enterprise features
- **UAT-driven quality** — Phase 35 UAT caught connector auto-registration bug (empty `__init__.py`); fix applied before milestone close
- **Competitive intelligence** — Referencing existing OSS projects (mcp-rag, qdrant-loader, local_faiss_mcp) informed design decisions for phases 29-37

### What Was Inefficient

- **Missing Phase 35 SUMMARY.md** — Phase 35 was executed but the plan's `output` instruction to create SUMMARY.md wasn't followed; had to be created retroactively at milestone close
- **CONTEXT.md questions never resolved** — 27 open design questions across 9 CONTEXT.md files were answered via code but never documented in the context files; had to be acknowledged as deferred at close
- **Phase 26-28 didn't have planning directories** — These were executed in a different session without creating `.planning/phases/` directories, creating a gap in execution history

### Patterns Established

- **Eager connector import registration** — `ingest/connectors/__init__.py` must eagerly import submodules for factory auto-registration
- **Resilience wrapper pattern** — `_try_provider()` + `_dispatch_with_resilience()` for provider fallback chain
- **Cache structured results** — Cache `list[dict]` before rendering, not rendered output
- **Version enumeration in env vars** — `KB_REGISTRY_DB_PATH` and similar for registry paths

### Key Lessons

1. **Plan output instructions must be verified** — Each plan with an `output` section specifying files to create needs verification at completion
2. **Context.md questions should be archived when resolved** — Either answer inline or note "resolved via code" to avoid open questions at milestone close
3. **Phase directory creation should be part of /gsd-init** — Ensures every phase has consistent artifact tracking
4. **Batch phases benefit from a coordinator pass** — The 2-wave structure (29-35, 36-37) worked well; consider structured wave planning for future multi-phase milestones

### Cost Observations

- Model: claude-sonnet-4.6 throughout
- Sessions: ~10 across 15 days
- Most expensive phases: Phase 29 (4 plans: foundation + 3 connectors) with the most file creation
- Notable: Phases 23 and 26-28 were lightweight (documentation + config), phases 29-37 were heavier (new modules, tests, schemas)

## Cross-Milestone Trends

| Milestone | Phases | Tests | Coverage | Duration |
|-----------|--------|-------|----------|----------|
| v1.0 | 4 | 491 | 88% | 5 days |
| v1.1 | 4 | 576 | 90% | 8 days |
| v1.2 | 4 | 585 | 90% | 13 days |
| v1.3 | 11 | 656 | 90% | 3 days |
| v1.4 | 13 | 1095 | 90% | 15 days |
