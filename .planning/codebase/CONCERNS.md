# Codebase Concerns

**Analysis Date:** 2026-05-19

## Tech Debt

**Duplicate `server/` and `kb_server/` modules:**
- Issue: Near-identical codebases exist in both `server/` and `kb_server/`. The `kb_server/` module is the newer, more feature-complete version (has `collections/` sub-package, multi-collection routing, `list_collections` MCP tool). The `server/` module is the older version still in use for some entry points and tests. Code that diverged from `server/` is never synced back.
- Files: `server/server.py`, `kb_server/server.py`, `server/embed_client.py`, `kb_server/embed_client.py`, `server/vector_store.py`, `kb_server/vector_store.py` (and all sub-packages)
- Impact: Bug fixes in one module are not reflected in the other. Tests that import from `server/` test outdated code. New features (multi-collection) only exist in `kb_server/`.
- Fix approach: Delete `server/` entirely; update all imports and tests to use `kb_server/`. The `server/` directory is the `server/` package from before the rename to `kb_server/`.

**`ingest/registry.py` (v1) is deprecated but still present:**
- Issue: The v1 registry (`data/registry.db`) was replaced by `ingest/core/metadata.py` (`data/kb_metadata.db`). The old `ingest/registry.py` still exists and some code may still reference it.
- Files: `ingest/registry.py`, `ingest/core/metadata.py`
- Impact: Two parallel registry systems. Migration logic in `ingest/core/metadata.py:188` handles v1→v2 migration but v1 file is never removed.
- Fix approach: After verifying all callers use `ingest/core/metadata.py`, remove `ingest/registry.py` and `data/registry.db`.

**`ingest/worker/batch_processor.py` uses placeholder checksum:**
- Issue: Batch-ingested documents use `checksum="batch"` as a hardcoded placeholder instead of computing an actual content hash.
- Files: `ingest/worker/batch_processor.py:278`
- Impact: Deduplication logic cannot detect re-ingested duplicate batch documents. The registry will re-ingest unchanged files on every batch run.
- Fix approach: Compute SHA-256 or xxhash (already a dependency) of file content before ingestion; pass as `checksum` field.

**`ingest/watcher/file_watcher.py` does not delete documents from Qdrant on file removal:**
- Issue: When the file watcher detects a deleted file it does NOT remove the corresponding vectors from Qdrant.
- Files: `ingest/watcher/file_watcher.py:191` — comment reads `# TODO: Implement deletion from Qdrant (future phase)`
- Impact: Stale, deleted documents remain searchable indefinitely. Knowledge base grows without bound and returns outdated results.
- Fix approach: Implement `on_deleted` handler in `FileWatcher` that calls `VectorStore.delete_by_filter(source_path=path)`.

**`.env` files are committed to git:**
- Issue: `.env`, `config/.env.local`, and `config/.env.lxc` are tracked by git (confirmed via `git ls-files`). The `.gitignore` only ignores `.venv/` not `.env` files.
- Files: `.env`, `config/.env.local`, `config/.env.lxc`
- Impact: Credentials (API keys, host addresses, passwords) are stored in version history. Rotating secrets does not eliminate exposure from git history.
- Fix approach: Add `*.env`, `.env*`, `config/.env*` to `.gitignore`. Use `git filter-branch` or `git-filter-repo` to remove from history. Move secrets to a secrets manager or document `config/.env.template` as the only committed file.

**`load_dotenv` is copy-pasted across 6+ entry points:**
- Issue: Every entry point (`server/server.py`, `server/health_server.py`, `ingest/ingest.py`, `ingest/cli/main.py`, `ingest/cli/legacy.py`, `ingest/watcher/file_watcher.py`) has its own manual `try: load_dotenv(...)` block with hardcoded project-relative paths.
- Files: All entry points listed above.
- Impact: If the project layout changes, each file must be updated independently. One missed update causes env vars to not load.
- Fix approach: Create a single `config/__init__.py` with a `bootstrap_env()` function; call it from entry points.

## Known Bugs

**Hybrid search always falls back to dense-only:**
- Symptoms: Hybrid search (`HybridSearcher`) claims to perform sparse+dense RRF fusion but the sparse search code path is commented out. The function returns dense-only results even when `strategy="hybrid"`.
- Files: `server/retrieval/hybrid_search.py:153-168`, `kb_server/retrieval/hybrid_search.py:153-168`
- Trigger: Any call to `search_kb` with hybrid mode enabled.
- Workaround: Results are still correct dense results, just not hybrid.

**`server/` module collections feature missing:**
- Symptoms: `server/server.py` does not have `list_collections` tool, `CollectionManager`, or `CollectionRouter`. Clients using the older `server/` entry point cannot use multi-collection features.
- Files: `server/server.py` (missing features present in `kb_server/server.py`)
- Trigger: Any tool invocation that relies on collection routing through the `server/` entry point.

## Security Considerations

**Committed `.env` files:**
- Risk: API keys, database passwords, embedding service credentials, and host configurations are stored in git history.
- Files: `.env`, `config/.env.local`, `config/.env.lxc`
- Current mitigation: None — files are tracked by git.
- Recommendations: Immediately rotate all credentials, purge from git history, add to `.gitignore`.

**No authentication on MCP server or health server:**
- Risk: `server/server.py` and `kb_server/server.py` expose MCP tools (search, ingest) with no authentication layer. The health server (`server/health_server.py`) also exposes system information without auth.
- Files: `server/server.py`, `kb_server/server.py`, `server/health_server.py`
- Current mitigation: Default binds to `127.0.0.1` (`SSE_HOST` default). Acceptable for local use, risky if `SSE_HOST=0.0.0.0`.
- Recommendations: Document that SSE mode must not be exposed publicly without a reverse proxy + auth layer.

**Broad exception swallowing in `ingest/classifier.py`:**
- Risk: `except Exception: pass` at lines 399, 423-425 silently ignores all errors during content classification. Malformed or malicious input may cause silent failures, making the system think classification succeeded when it didn't.
- Files: `ingest/classifier.py:399`, `ingest/classifier.py:423-425`
- Current mitigation: None.
- Recommendations: Log exceptions at WARNING level at minimum; re-raise if critical.

## Performance Bottlenecks

**No CI/CD pipeline — tests run manually:**
- Problem: No `.github/workflows/` directory exists. Tests must be run manually. This was deferred in FASE 1 (`TRANSITION.md:17`).
- Files: Entire `tests/` directory lacks automation.
- Cause: Explicit deferral to focus on feature development.
- Improvement path: Add GitHub Actions workflow running `pytest tests/ -x --ignore=tests/e2e` on push/PR.

**SQLite used for job queue under concurrent worker load:**
- Problem: `ingest/job/manager.py` uses SQLite (`kb_metadata.db`) as the job queue backend. Under concurrent batch processing (`ingest/worker/pool.py` spawns multiple workers), SQLite write contention becomes a bottleneck.
- Files: `ingest/job/manager.py`, `ingest/worker/pool.py`, `ingest/worker/batch_processor.py`
- Cause: SQLite has a single-writer limitation; WAL mode helps but doesn't eliminate contention.
- Improvement path: Enable WAL mode explicitly (`PRAGMA journal_mode=WAL`); or migrate to PostgreSQL/Redis for job queue at scale.

## Fragile Areas

**Test suite heavily relies on `sys.modules` monkey-patching:**
- Files: `tests/test_smoke.py`, `tests/test_hybrid_search.py`, `tests/test_payload_indexes.py`, `tests/test_reranker.py`, `tests/test_hybrid_rrf.py`
- Why fragile: Tests inject stub modules into `sys.modules` before imports. If import order changes, or test isolation between files is broken, stubs from one test file bleed into another.
- Safe modification: Always run tests in fresh subprocess isolation (`pytest-xdist` with `--forked`) rather than relying on manual `sys.modules` patching.
- Test coverage: Core MCP server logic (`server.py`, `kb_server/server.py`) has minimal unit test coverage; most tests cover auxiliary components.

**`qa/embedder.py` and `qa/run_qa.py` must import `kb_server` before `mcp`:**
- Files: `qa/embedder.py:8`, `qa/run_qa.py:19`
- Why fragile: Comment reads "must be imported before mcp pollutes sys.modules". This ordering dependency is invisible to tooling and will silently break if import order is changed.
- Safe modification: Document the constraint; consider a module-level guard or import hook.

**`ingest/cli/main.py` uses `E402` noqa suppressions for critical imports:**
- Files: `ingest/cli/main.py:27-29`
- Why fragile: The `load_dotenv` must run before CLI group imports (which read env vars at import time). This ordering is enforced only by comment + noqa suppression — refactoring the file structure could silently break env var loading.
- Safe modification: Centralize env bootstrap in a top-level utility imported first.

## Missing Critical Features

**No CI/CD automation:**
- Problem: Deferred in FASE 1, never implemented. The project has 339 test functions but no automated runner.
- Blocks: Confident merging, regression detection, release automation.

**Sparse search is stubbed out (not implemented):**
- Problem: The hybrid search feature advertised in documentation (`docs/SEARCH_QUALITY.md`) is not actually performing sparse vector search. Sparse search code is commented out in both `server/retrieval/hybrid_search.py` and `kb_server/retrieval/hybrid_search.py`.
- Blocks: True BM25/hybrid RAG quality; claimed FASE features are incomplete.

**RAGAS evaluation pipeline is not implemented:**
- Problem: `kb_server/evaluation/ragas_pipeline.py:47-53` and `server/evaluation/ragas_pipeline.py:47-53` contain a TODO and `raise NotImplementedError`. The `docs/RAG_EVALUATION.md` references this pipeline.
- Blocks: Automated RAG quality measurement.

**Chunking and scoring experiment runners are stubs:**
- Problem: `kb_server/optimization/chunking_experiments.py` and `kb_server/optimization/scoring_experiments.py` (and their `server/` equivalents) immediately `raise NotImplementedError`.
- Blocks: Parameter tuning for retrieval quality.

## Test Coverage Gaps

**`kb_server/collections/` (multi-collection routing):**
- What's not tested: `CollectionManager` and `CollectionRouter` behavior under missing collections, alias resolution, error propagation to MCP tools.
- Files: `kb_server/collections/manager.py`, `kb_server/collections/router.py`
- Risk: Multi-collection feature (FASE 15) could fail silently.
- Priority: High

**`ingest/watcher/file_watcher.py` deletion path:**
- What's not tested: The `on_deleted` file event (the TODO path). `tests/test_file_watcher.py` exists but may not cover the deletion stub.
- Files: `ingest/watcher/file_watcher.py:191`
- Risk: Stale data accumulates undetected.
- Priority: High

**`server/` module (old entry point):**
- What's not tested: The `server/` module has drifted from `kb_server/` and tests that import from `server/` are testing outdated code. Any bug in `server/` is masked.
- Files: `server/server.py`, `server/embed_client.py`, `server/vector_store.py`
- Risk: Production environments still using `server/` entry point are unprotected by the test suite.
- Priority: Medium (resolve by deleting `server/` and using `kb_server/` exclusively)

---

*Concerns audit: 2026-05-19*
