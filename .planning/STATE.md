---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Quality & Operational Excellence
status: planning
last_updated: "2026-05-21T20:49:12.738Z"
last_activity: 2026-05-21
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-19)

**Core value:** AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.
**Current focus:** v1.0 shipped — planning next milestone with `/gsd-new-milestone`

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-05-21 — Milestone v1.1 started

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
