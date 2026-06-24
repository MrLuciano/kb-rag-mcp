# Ingestion Schedule Feature Design

## Problem
The Admin UI Ingestion → Schedule tab shows a placeholder with no functionality. Users need to create CRON-based ingestion schedules and monitor their execution.

## Solution
Add a `schedules` table to the existing `kb_metadata.db` (schema v6), CRUD API endpoints, a lightweight cron matcher (pure Python, no deps), an asyncio background scheduler loop, and an Alpine.js-driven schedule management UI.

## Data Model

### `schedules` table (in `kb_metadata.db`)
| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PRIMARY KEY | UUID |
| `name` | TEXT NOT NULL | Human label |
| `cron_expr` | TEXT NOT NULL | Standard 5-field cron (`min hour dom mon dow`) |
| `docs_path` | TEXT NOT NULL | Directory to ingest |
| `product` | TEXT | Product name override (optional) |
| `workers` | INTEGER DEFAULT 2 | Parallel worker count |
| `priority` | TEXT DEFAULT 'normal' | low/normal/high/critical |
| `clean` | INTEGER DEFAULT 0 | Clean before ingest |
| `force` | INTEGER DEFAULT 0 | Force reingest |
| `enabled` | INTEGER DEFAULT 1 | Schedule active toggle |
| `created_at` | REAL | Unix timestamp |
| `updated_at` | REAL | Unix timestamp |
| `last_run_at` | REAL | Last job creation time |
| `last_run_status` | TEXT | Last job status (pending/completed/failed) |
| `next_run_at` | REAL | Computed next cron match time |

Fields match `kb-rag job create` CLI options.

## Cron Expression Format

Standard 5-field: `minute hour day-of-month month day-of-week`
- All fields support: `*`, `*/N`, `N-M`, comma-separated lists
- Pure Python implementation in `ingest/core/cron.py` — no external dependencies

## API Endpoints

New router `kb_server/schedules/router.py` mounted at `/api/v1/schedules`:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/schedules` | List all schedules |
| `POST` | `/api/v1/schedules` | Create schedule |
| `PUT` | `/api/v1/schedules/{id}` | Update schedule |
| `DELETE` | `/api/v1/schedules/{id}` | Delete schedule |

Auth: Uses same `_verify_config_auth` pattern (API key or session cookie).

## Background Scheduler

An asyncio task started during server initialization (`kb_server/server.py` startup):

1. Every 30 seconds, query `schedules WHERE enabled=1 AND next_run_at <= now()`
2. For each match, create a `Job` via `JobManager.create_job()` with the schedule's params
3. Update `last_run_at = now()`, `last_run_status = 'pending'`, compute `next_run_at`
4. Log schedule execution

The `next_run_at` is computed by: starting from the most recent of `last_run_at` or `created_at`, walk forward minute-by-minute checking `cron_matches()` until we find a future match. Walk limited to 525600 minutes (1 year) to prevent infinite loops. Schedules with `next_run_at IS NULL` on first scheduler pass get their `next_run_at` computed automatically.

## UI

### Schedule Tab (`_ingestion_schedule.html`)

**Top: Create/Edit form**
- Name (text input)
- CRON expression (text input, with placeholder showing format)
- Docs path (text input, directory)
- Product (text input, optional)
- Workers (number input, default 2)
- Priority (select: low/normal/high/critical)
- Clean (checkbox)
- Force (checkbox)
- Save / Cancel buttons

**Bottom: Schedule list table**
- Name, CRON expression, docs path, enabled toggle, Next run, Last run, Actions (Edit/Delete)
- Enabled toggle switches via `PUT /api/v1/schedules/{id}`

### Monitor Tab
No changes needed — existing `job-status` partial shows all jobs including those created by schedules.

## Implementation Order

1. `ingest/core/cron.py` — pure Python cron matcher (`cron_matches()`, `next_cron_time()`)
2. `ingest/core/metadata.py` — schema v6 migration + Schedule CRUD methods
3. `ingest/job/models.py` — `Schedule` dataclass (light, reuses existing patterns)
4. `kb_server/schedules/router.py` — API CRUD endpoints
5. `kb_server/server.py` — background scheduler loop registration
6. `kb_server/ui/templates/admin/_ingestion_schedule.html` — schedule form + list UI
7. `kb_server/ui/templates/admin/shell.html` — `scheduleManager` Alpine component
8. Wire up router in `kb_server/ui/app.py`
9. Docker deploy + verify

## Error Handling
- Invalid cron expressions: validated on create/update, return 422 with field-level error
- Duplicate schedule names: validated with 409 Conflict
- Missing required fields: 422
- Schedule not found: 404
- Scheduler failures: logged but never crash the server
