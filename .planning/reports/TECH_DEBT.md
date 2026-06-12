# Technical Debt & Backlog — Consolidated for Next Milestone

**Generated:** 2026-05-23
**Scope:** v0.1.0 (Release-Readiness) + v0.1.1 (Quality & Operational Excellence)
**Purpose:** Input for next milestone planning — prioritized by impact, with remediation guidance.

---

## Legend

| Label | Meaning |
|-------|---------|
| 🔴 **Must fix** | Blocks correctness, deployment, or user experience |
| 🟡 **Should fix** | Developer friction, suboptimal patterns, deferred improvements |
| 🟢 **Nice to have** | Polish, convenience, future-proofing |
| 📦 **Backlog** | Feature work, not debt — sized for a future milestone |

---

## 🔴 Must Fix

### M-01: KB has zero documents
**Source:** v0.1.1 operational · **Effort:** ~30 min
**Issue:** The OTCS documentation on acemagic (`/mnt/c/Recebedor/learning/`) has never been ingested. Server returns empty results for all queries.
**Remediation:** SSH into acemagic, `git pull`, `source .venv/bin/activate`, `kb-ingest ingest --docs /mnt/c/Recebedor/learning/`.
**Blocks:** All downstream user value — nothing to search.

### M-02: LM Studio must be running for any ingest/eval
**Source:** v0.1.0 operational · **Effort:** ~2h
**Issue:** Embedding backend dependency — LM Studio (or Ollama/OpenAI-compat server) at `http://<LM_STUDIO_HOST>:1234` must be running for all ingest pipeline operations. No graceful fallback or offline mode.
**Remediation options:**
- Document the dependency prominently in ops docs (quick win)
- Add startup health-check that warns if LM Studio is unreachable
- Support a fallback embedding backend (e.g., `sentence-transformers` local model) for dev/offline use
- Add `kb-ingest check` command that validates all external deps

---

## 🟡 Should Fix

### S-01: Cross-encoder model loads 500MB+ at import time
**Source:** v0.1.1 (Phase 6 deferred) · **Effort:** ~1h
**Issue:** `kb_server/retrieval/reranker.py` loads `sentence_transformers.CrossEncoder` at module import time (not on first use). This adds ~500MB memory and ~10s startup even if reranking is never called. Unit tests must mock the entire module to avoid triggering the load.
**Remediation:** Defer model loading to first `predict()` call via `@lru_cache` on a private `_get_model()` function or similar lazy-init pattern.
**Files:** `kb_server/retrieval/reranker.py`
**Pattern to follow:** Lazy loading pattern used elsewhere in the codebase (e.g., sparse model in `hybrid_search.py`).

### S-02: `helm` chart not validated in CI
**Source:** v0.1.0 tech debt · **Effort:** ~30 min
**Issue:** `helm lint` never runs because helm is not installed in the WSL dev environment. Kubernetes chart structure is reviewed by inspection only.
**Remediation:** Add a CI job that installs helm and runs `helm lint` on the chart. Or add a `scripts/validate-chart.sh` that checks the chart structurally.
**Files:** `.github/workflows/ci.yml`, `deployment/helm/kb-rag-mcp/`

### S-03: MagicMock pollution from `qdrant_client` stubs
**Source:** v0.1.0 tech debt · **Effort:** ~2h (exploratory)
**Issue:** Module-level stubbing of `qdrant_client` in `sys.modules` causes downstream enum values (`CollectionStatus`, `PayloadSchemaType`, etc.) to be MagicMock instances instead of real enums. Mitigated with `getattr(x, 'value', x)` pattern, but the pattern is fragile and not applied consistently.
**Related:** `PayloadSchemaType` assertion weakened in `test_payload_indexes.py`; 1 assertion removed from `test_create_index_on_new_collection`.
**Remediation options:**
- Switch from `sys.modules` stubbing to `unittest.mock.patch` with explicit targets
- Or, replace stubbed modules with `qdrant-client`-provided test utilities (if any)
- Or, document all affected files and accept the pattern as established convention
**Files:** `tests/test_vector_store_unit.py`, `tests/test_payload_indexes.py`, `tests/conftest.py`

### S-04: No startup dependency check
**Source:** v0.1.1 operational gap · **Effort:** ~1h
**Issue:** The server starts successfully even when Qdrant or LM Studio are unreachable. Failures only surface on first query or ingest. No pre-flight check.
**Remediation:** Add `kb-ingest check` or server startup health validation that verifies:
1. Qdrant is reachable (HTTP ping to `/healthz`)
2. Embedding backend responds (HTTP ping to models endpoint)
3. SQLite databases are writable
**Pattern:** Extend `kb_server/health_server.py` or create a new `scripts/diagnostics.py`.

### S-05: Logging audit script is informational, not a gate
**Source:** v0.1.1 (Phase 7) · **Effort:** ~30 min
**Issue:** `scripts/logging-audit.py` produces a report but is not enforced in CI. Logging coverage could regress without detection. 3 modules at 71-86% coverage (utility methods exempted).
**Remediation:** Add a `--fail-under` flag to the audit script and a CI job running it on PR-to-master. Set initial threshold at 50% (current baseline) and ratchet up.
**Files:** `scripts/logging-audit.py`, `.github/workflows/ci.yml`

---

## 🟢 Nice to Have

### N-01: Docstring audit script is informational, not a gate
**Source:** v0.1.1 (Phase 8) · **Effort:** ~30 min
**Issue:** `scripts/docstring-audit.py` produces a report but is not enforced in CI. Docstring coverage could regress.
**Remediation:** Add `--fail-under` flag + CI enforcement step, same pattern as S-05.

### N-02: No clean-machine test for `quickstart.sh`
**Source:** v0.1.0 retrospective · **Effort:** ~2h
**Issue:** `scripts/quickstart.sh` is validated by inspection only. A Docker-based clean-room test would catch env assumptions.
**Remediation:** Create `tests/test_quickstart.sh` that spins up a throwaway container, runs quickstart.sh, and verifies the server responds.

### N-03: SSE tests run in a separate CI process
**Source:** v0.1.1 (Phase 5) · **Effort:** ~1h
**Issue:** SSE handler tests must run in a separate `python -m pytest` process from all other tests due to `test_smoke.py` module-level stubs. This adds CI complexity and a ~15s overhead.
**Remediation:** Refactor `test_smoke.py` to use per-function `@patch` instead of module-level `sys.modules` stubs, allowing SSE tests to run in the same process.

### N-04: `asyncio_mode = STRICT` means every async test needs a marker
**Source:** v0.1.0 architecture · **Effort:** ongoing
**Issue:** Forgetting `@pytest.mark.asyncio` on an async test causes it to silently pass without executing. This is by design but is a frequent source of CI confusion.
**Remediation:** Better documentation in test templates; or explore `asyncio_mode = AUTO` if pyproject.toml can be safely changed (risk: backward-compat with existing tests).

### N-05: Utility/accessor methods exempt from logging audit
**Source:** v0.1.1 (Phase 7) · **Effort:** low
**Issue:** Methods like `hash_key`, `backend_type`, `conn`, `sha256` are exempt from log coverage requirements. The exemption is defined informally. Should be documented in the audit script's configuration.
**Remediation:** Add an `EXEMPT_METHODS` constant to `scripts/logging-audit.py` with inline documentation.

### N-06: `helm` chart needs a documented review checklist
**Source:** v0.1.0 tech debt · **Effort:** ~30 min
**Issue:** Until `helm lint` runs in CI (S-02), chart reviews are manual. No checklist exists for what to verify.
**Remediation:** Add a REVIEW_CHECKLIST.md in `deployment/helm/kb-rag-mcp/` covering: values.yaml required fields, image tag strategy, resource limits, probe paths.

---

## 📦 Backlog (Feature Work)

These are feature-sized items from the ROADMAP backlog. Not debt — sized for future milestones.

### B-01: English inline comments sweep (Backlog 999.1)
**Effort:** ~1h · **Depends on:** Nothing
**Goal:** Audit and translate all inline (`#`) comments in Python source files to English. Docstrings were covered in v0.1.1 Phase 8, but inline comments may still have Portuguese.
**Verification:** Extend `scripts/docstring-audit.py` (or create `scripts/comments-audit.py`) to scan for Portuguese inline comments.

### B-02: README translations + Spanish README (Backlog 999.2)
**Effort:** ~3h · **Depends on:** Nothing
**Goal:** Sync `docs/` with all v0.1.1 changes (already partially done in Phase 8), update `README.pt-BR.md`, add `README.es.md`.
**Notes:** Phase 8 already updated `docs/INDEX.md`, `docs/OPERATIONS.md`, `docs/REFERENCE.md`, `docs/ARCHITECTURE.md` — but `README.md` and `README.pt-BR.md` were not included.

### B-03: System health dashboard (Backlog 999.3)
**Effort:** ~4h · **Depends on:** S-04
**Goal:** Single-page dashboard consolidating Qdrant health, MCP server status, ingest status. Served via a lightweight httpd pod (nginx/Caddy) or via FastAPI.
**Pattern:** Extend `kb_server/health_server.py` or create a new `kb_server/dashboard/` module.

### B-04: PowerShell port script (Backlog 999.4)
**Effort:** ~30 min · **Depends on:** Nothing
**Goal:** `scripts/start-kb-rag.ps1` should automatically open required ports (6333/6334 for Qdrant, 8765 for SSE, 8080 for health) using `netsh` or `New-NetFirewallRule`.

### B-05: Auto-classification — Vendor/Product/Version (Backlog 999.5)
**Effort:** ~6h · **Depends on:** Nothing
**Goal:** Extend `ingest/classifier.py` to infer Vendor, Product, Subsystem, Version from filename patterns, directory path, and first-page content (title/header/footer). Pattern: `OpenText Documentum Webtop Administrator Guide 23.4.pdf`.
**Notes:** v0.1.1 Phase 8 added OTCS product auto-tagging (10 products) — this is a superset that adds Vendor, Subsystem, Version dimensions.

### B-06: Reclassification for ingested docs (Backlog 999.6)
**Effort:** ~4h · **Depends on:** B-05
**Goal:** When auto-classification is ready, provide a mechanism to reclassify already-ingested documents — either update metadata in Qdrant + SQLite, or re-ingest with new metadata.
**Warning:** Re-ingestion is expensive (re-embeds all chunks). Prefer in-place metadata update when possible.

---

## Deprecated / Already Handled

These items appeared in earlier tech debt tracking but have been resolved or are no longer relevant:

| Item | Source | Status |
|------|--------|--------|
| Rich markup `[/{variable}]` → `[/]` bugs | v0.1.0 | Fixed in v0.1.0 Phase 1 |
| Missing `f`-string prefixes in CLI | v0.1.0 | Fixed in v0.1.0 Phase 3 |
| 19 pre-existing test failures | v0.1.0 | 18 fixed; 1 removed assertion (see S-03) |
| `test_smoke.py` module-level starlette stubs | v0.1.1 | Mitigated — SSE tests run in separate process (see N-03) |
| `server/` legacy package references in docs | v0.1.1 | Fixed in v0.1.1 Phase 8 docs refresh |
| Portuguese docstrings | v0.1.1 | All translated to English in v0.1.1 Phase 8 |
| Missing English docstrings on public APIs | v0.1.1 | All filled in v0.1.1 Phase 8 |

---

## Summary by Priority

| Priority | Count | Key Items |
|----------|-------|-----------|
| 🔴 Must fix | 2 | Empty KB, LM Studio dependency |
| 🟡 Should fix | 5 | Lazy-load reranker, helm CI, MagicMock pollution, startup check, logging gate |
| 🟢 Nice to have | 6 | Docstring gate, quickstart validation, SSE process merge, strict mode docs, audit exemptions, helm checklist |
| 📦 Backlog | 6 | Comments sweep, README translations, dashboard, PS script, auto-classification, reclassification |
| **Total** | **19** | |

---

*Next step: Use this document with `/gsd-review-backlog` to promote items into the next milestone.*
