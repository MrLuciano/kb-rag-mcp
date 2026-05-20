---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Release-Readiness
status: complete
stopped_at: "v1.0 milestone closed — all 4 phases shipped, 15/15 requirements met."
last_updated: "2026-05-19T00:00:00.000Z"
last_activity: 2026-05-19 -- v1.0 milestone closed; 491 tests passing, 88% kb_server branch coverage
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 13
  completed_plans: 13
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-19)

**Core value:** AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.
**Current focus:** v1.0 shipped — planning next milestone with `/gsd-new-milestone`

## Current Position

Milestone: v1.0 — SHIPPED 2026-05-19
All 4 phases complete. All 15 v1 requirements met.
Next: Run `/gsd-new-milestone` to define v1.1 requirements and roadmap.

## Accumulated Context

### Key Decisions (v1.0)
- `kb_server/` is single canonical module; `server/` deleted
- `bootstrap_env()` in `config/` — single env-loading entry point
- `IngestRegistry` → `ingest/core/metadata.py`
- fastembed BM25 for sparse vectors (embedded, no separate server)
- `asyncio_mode = STRICT` — all async tests need `@pytest.mark.asyncio`
- MagicMock pollution from qdrant_client stubs — use `getattr(x, 'value', x)` pattern for enum comparisons

### Known Tech Debt
- `PayloadSchemaType` assertion weakened in `test_payload_indexes.py`
- `helm lint` not validated (helm not installed in WSL dev)
- LM Studio must be running locally for live ingest/eval
