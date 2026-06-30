---
phase: 52-ingestion-schedule
plan: 01
subsystem: ingest
tags: [cron, schedule, admin-ui, scheduler, metadata]
requires:
  - phase: 28c
    provides: Admin SPA shell with Ingestion tab
  - phase: 45
    provides: Database reliability patterns, MetadataStore schema v5
provides:
  - Pure Python 5-field cron matcher (98% branch coverage)
  - Schema v6 migration: schedules table + CRUD methods
  - Schedules FastAPI router at /api/v1/schedules
  - Background asyncio scheduler loop (30s interval)
  - Schedule management UI in Admin Ingestion tab
affects:
  - kb_server/server.py
  - kb_server/ui/app.py
  - ingest/core/metadata.py
tech-stack:
  added: []
  patterns:
    - "Cron matching: pure Python 5-field with * /N N-M comma list support"
    - "Background scheduler: asyncio task polling every 30s, never crashes server"
    - "Schedule CRUD: MetadataStore methods + FastAPI router + Alpine.js UI"
requirements-completed:
  - SCHED-01
  - SCHED-02
  - SCHED-03
  - SCHED-04
  - SCHED-05
duration: ~2h
completed: 2026-06-26
status: complete
---

# Phase 52 Plan 01: Ingestion Schedule Management

**Implementation: Cron matcher, schedule CRUD, API router, background scheduler, Admin UI.**

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/test_cron_matcher.py -v` | ✅ 42/42 PASS |
| `pytest tests/test_schedule_metadata.py -v` | ✅ 27/27 PASS |
| `pytest tests/test_admin_ui.py -v` | ✅ All pass |
| Full suite (1501 tests) | ✅ No regressions |
| Branch coverage (overall) | ✅ 72% |

## Tasks Executed

| # | Task | Status | Commit |
|---|------|--------|--------|
| 1 | `ingest/core/cron.py` — Pure Python 5-field cron matcher: `cron_matches()`, `next_cron_time()` | ✅ | e191bc0 |
| 2 | MetadataStore v6 migration: `schedules` table + `add/list/get/update/delete_schedule()`, `compute_next_run()` | ✅ | e191bc0 |
| 3 | `kb_server/schedules/router.py` — FastAPI CRUD router at `/api/v1/schedules` with cron validation, auth | ✅ | e191bc0 |
| 4 | `kb_server/server.py` — Background scheduler asyncio task (30s interval), `_init_schedule_checker()` | ✅ | e191bc0 |
| 5 | `_ingestion_schedule.html` + `scheduleManager` Alpine component — form + table + edit modal | ✅ | e191bc0 |
| 6 | Wire up: router in `kb_server/ui/app.py`, deploy to Docker | ✅ | e191bc0 |

## Files Created/Modified

- `ingest/core/cron.py` — New: pure Python cron matcher (103 lines, 98% branch coverage)
- `ingest/core/metadata.py` — Schema v6 migration, Schedule CRUD methods (190 lines added)
- `ingest/job/models.py` — Schedule dataclass
- `kb_server/schedules/__init__.py` — Package init
- `kb_server/schedules/router.py` — FastAPI CRUD router (145 lines)
- `kb_server/server.py` — Background scheduler, `_init_schedule_checker()` (101 lines added)
- `kb_server/ui/app.py` — Router mount, MetadataStore init
- `kb_server/ui/templates/admin/_ingestion_schedule.html` — Schedule management UI (143 lines)
- `kb_server/ui/templates/admin/shell.html` — scheduleManager Alpine component (160 lines added)
- `kb_server/ui/templates/admin/_users_table.html` — Modal pattern reuse (41 lines)
- `tests/test_cron_matcher.py` — 42 tests
- `tests/test_schedule_metadata.py` — 27 tests

## Key Decisions

- Pure Python cron matcher (no external deps) — avoids adding croniter or similar
- Background scheduler runs in asyncio task — non-blocking, 30s interval
- Schedules persist in SQLite via MetadataStore — survive server restarts
- Auth via `_verify_config_auth` — same pattern as config API (API key or session cookie)
- Duplicate name validation with 409 Conflict
- Invalid cron expressions return 422 with field-level errors

## Monitoring Integration

Existing job monitor shows scheduled jobs automatically (they use JobManager.create_job()).
No UI changes needed — `_ingestion_monitor.html` is already job-status aware.
