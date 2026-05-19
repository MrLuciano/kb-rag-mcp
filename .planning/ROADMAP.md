# Roadmap: kb-rag-mcp (Release-Readiness Milestone)

## Overview

All 16 features are implemented and working. This milestone closes integration gaps, removes technical debt, hardens deployment, and raises test coverage — making the project safe to release publicly. Four coarse phases deliver coherent, verifiable capabilities in dependency order.

## Phases

- [ ] **Phase 1: Codebase Consolidation** - Delete legacy module, fix bugs, unify env loading
- [ ] **Phase 2: Data Integrity & Security** - File watcher deletion, env cleanup, contributing guide
- [ ] **Phase 3: Test Coverage & CI** - ≥80% branch coverage, integration tests, GitHub Actions
- [ ] **Phase 4: Deployment & Release** - Dockerfile, quickstart script, README getting-started guide

## Phase Details

### Phase 1: Codebase Consolidation
**Goal**: The codebase has one canonical module (`kb_server/`), real deduplication, and a single env-loading entry point
**Depends on**: Nothing (first phase)
**Requirements**: CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04, CLEAN-05
**Success Criteria** (what must be TRUE):
  1. `server/` directory is deleted; `grep -r "from server" .` returns no results in source files
  2. Hybrid search performs real BM25+dense RRF fusion — a unit test proves sparse path is exercised
  3. All entry points call `bootstrap_env()` — `grep -r "load_dotenv" .` finds only the one canonical definition
  4. `ingest/registry.py` is deleted; only `ingest/core/metadata.py` remains
  5. Batch ingest computes real SHA-256 checksums — test proves two identical files deduplicate, two different files don't
**Plans**: 4 plans

Plans:
- [ ] 01-01-PLAN.md — Delete legacy `server/` module, verify zero external imports
- [ ] 01-02-PLAN.md — Create `config/bootstrap_env()`, replace 9 `load_dotenv` blocks
- [ ] 01-03-PLAN.md — Implement real BM25+dense RRF hybrid search + unit test
- [ ] 01-04-PLAN.md — Move IngestRegistry to `ingest/core/metadata.py`, fix batch SHA-256

### Phase 2: Data Integrity & Security
**Goal**: Stale docs are removed from Qdrant on file deletion, no secrets are tracked in git, and teams have a clear remediation guide
**Depends on**: Phase 1
**Requirements**: DATA-01, DATA-02, DATA-03
**Success Criteria** (what must be TRUE):
  1. Deleting a watched file causes its vectors to be removed from Qdrant — verified by integration test
  2. `git ls-files | grep ".env"` returns only `config/.env.template`; no real values in tracked files
  3. `CONTRIBUTING.md` exists with step-by-step `git-filter-repo` instructions for secret removal
**Plans**: TBD

### Phase 3: Test Coverage & CI
**Goal**: `kb_server/` has ≥80% branch coverage, integration tests cover critical paths, and CI runs on every push
**Depends on**: Phase 2
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. `pytest --cov=kb_server --cov-report=term` reports ≥80% branch coverage
  2. Integration test: ingest a document → `search_kb` MCP tool returns that document in results
  3. Integration test: multi-collection routing sends queries to the correct collection and gracefully falls back when a collection is missing
  4. GitHub Actions workflow file exists; a push to `master` triggers a passing CI run
**Plans**: TBD

### Phase 4: Deployment & Release
**Goal**: Any team can go from zero to a working RAG server using only the published instructions
**Depends on**: Phase 3
**Requirements**: DEPL-01, DEPL-02, DEPL-03
**Success Criteria** (what must be TRUE):
  1. `docker build .` produces a working image; `docker run` starts the MCP server without errors
  2. `bash scripts/quickstart.sh` completes end-to-end (clone → configure → start → health check) on a clean machine
  3. README contains a getting-started section covering: install, configure `.env`, ingest docs, connect an AI tool — verified by walkthrough
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Codebase Consolidation | 0/TBD | Not started | - |
| 2. Data Integrity & Security | 0/TBD | Not started | - |
| 3. Test Coverage & CI | 0/TBD | Not started | - |
| 4. Deployment & Release | 0/TBD | Not started | - |
