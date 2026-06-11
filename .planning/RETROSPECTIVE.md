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

## Cross-Milestone Trends

| Milestone | Phases | Tests | Coverage | Duration |
|-----------|--------|-------|----------|----------|
| v1.0 | 4 | 491 | 88% | 5 days |
