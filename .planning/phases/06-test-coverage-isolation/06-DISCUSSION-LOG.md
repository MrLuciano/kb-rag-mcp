# Phase 6: Test Coverage & Isolation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** 6-Test-Coverage-Isolation
**Areas discussed:** Module-to-test-file mapping, Test isolation for embedding models

---

## Module-to-Test-File Mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Strict 1:1 | Every .py file gets a test_*.py | |
| Per-subject grouping | One test file per functional area | |
| Hybrid | 1:1 for uncovered modules, grouping for covered areas | ✓ |

**User's choice:** Hybrid — 1:1 for literally uncovered modules, grouping for covered areas
**Notes:** User clarified that ALL modules without a dedicated test file need one, not just classifier.py. New test files should use a mix of unit with mocking and integration markers where impractical to mock.

---

## Test Isolation for Embedding Models

| Option | Description | Selected |
|--------|-------------|----------|
| Mock at model level | Patch CrossEncoder with MagicMock | |
| Skip with marker | @pytest.mark.skipif for CI flag | |
| Lazy load | Refactor to defer model loading | ✓ (deferred) |

**User's choice:** Lazy load (deferred to post-Phase 6). For now, mock with @patch.
**Notes:** Integration marker policy: only for tests needing external RUNNING SERVICES (Qdrant container, LM Studio, Redis). Tests loading local models are "unit" for tagging purposes.

---

## Deferred Ideas

- Lazy-load cross-encoder model in `kb_server/retrieval/reranker.py` — post-Phase 6 optimization
