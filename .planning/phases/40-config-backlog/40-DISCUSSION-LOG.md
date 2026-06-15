# Phase 40: Configuration Backlog - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 40-config-backlog
**Areas discussed:** ConfigLoader design, API server placement, Type validation, Database & connections, Hot-reload propagation

---

## ConfigLoader Design

| Option | Description | Selected |
|--------|-------------|----------|
| Replace inline os.getenv() (Recommended) | ConfigLoader.get() is single source of truth — SQLite → .env → default. Refactor module-level calls. | ✓ |
| Keep os.getenv() + API overlay | Keep existing os.getenv() calls, ConfigLoader sits behind REST API only | |
| Hybrid: ConfigLoader at bootstrap | ConfigLoader.get() exists but only in new code; old os.getenv() calls remain | |

**User's choice:** Replace inline os.getenv()
**Notes:** Single source of truth across all config.

| Option | Description | Selected |
|--------|-------------|----------|
| Silent degradation (Recommended) | Log warning, fall through .env → os.getenv default | ✓ |
| Hard fail on startup | Raise ConfigurationError if SQLite unavailable | |

**User's choice:** Silent degradation
**Notes:** CONF-08 compliant.

| Option | Description | Selected |
|--------|-------------|----------|
| Early bootstrap + dynamic lookup (Recommended) | Load SQLite values during bootstrap_env(), after dotenv but before service code | ✓ |
| Lazy first-access | Load SQLite values on first ConfigLoader.get() call | |

**User's choice:** Early bootstrap + dynamic lookup

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory dict + version check (Recommended) | Cache all SQLite config in dict, lightweight version counter for hot-reload detection | ✓ |
| SQLite read every call | Uncache — every ConfigLoader.get() hits SQLite | |
| Read-through cache with TTL | Configurable TTL for cache expiry | |

**User's choice:** In-memory dict + version check

---

## API Server Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Health server (port 8000) (Recommended) | Mount config router on existing FastAPI health_server.py | ✓ |
| Admin SPA server (port 8001) | Mount on admin SPA FastAPI server | |
| Dedicated config server | New standalone FastAPI server on new port | |

**User's choice:** Health server (port 8000)
**Notes:** Reuses existing infrastructure.

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed path (Recommended) | Mount at /api/v1/config | ✓ |
| Configurable prefix | Env var for path prefix | |

**User's choice:** Fixed path

| Option | Description | Selected |
|--------|-------------|----------|
| No auth initially (Recommended) | Matches health server pattern | ✓ |
| Require auth from start | But circular dependency with Phase 28b (Auth API needs JWT secret from config) | |

**User's choice:** No auth initially

---

## Type Validation

| Option | Description | Selected |
|--------|-------------|----------|
| string, int, float, bool (Recommended) | Common types | |
| string, int, float, bool, json, list | Extended types with JSON validation and comma-separated lists | ✓ |

**User's choice:** string, int, float, bool, json, list

| Option | Description | Selected |
|--------|-------------|----------|
| HTTP 422 with field-level errors (Recommended) | `{\"error\":\"Validation failed\",\"field\":\"value\",\"type\":\"int\",\"reason\":...}` | ✓ |
| HTTP 400 with generic message | `{\"error\":\"Invalid value for config key ...\"}` | |

**User's choice:** HTTP 422 with field-level errors

| Option | Description | Selected |
|--------|-------------|----------|
| Upsert (Recommended) | PUT creates key if not exists; seed from env vars on first run | ✓ |
| Update only | PUT only works for existing keys | |

**User's choice:** Upsert

| Option | Description | Selected |
|--------|-------------|----------|
| Required in request body (Recommended) | PUT body must include group and description | ✓ |
| Auto-populated | group defaults to 'custom', description to 'Configured via API' | |

**User's choice:** Required in request body

---

## Database & Connection Management

| Option | Description | Selected |
|--------|-------------|----------|
| Own connection pool (Recommended) | ConfigLoader creates own SQLite connection(s) to kb_metadata.db | ✓ |
| Shared with query_logger | Reuse query_logger's existing connection | |

**User's choice:** Own connection pool

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-create (Recommended) | CREATE TABLE IF NOT EXISTS during bootstrap | ✓ |
| Migration script only | Manual migration step | |

**User's choice:** Auto-create

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, enable WAL (Recommended) | PRAGMA journal_mode=WAL for concurrent reads | ✓ |
| No — default journal mode | Default SQLite journal mode | |

**User's choice:** Yes, enable WAL

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated db.py helper (Recommended) | kb_server/config/db.py with get_connection() contextmanager | ✓ |
| Inline sqlite3 in ConfigLoader | Create connections directly | |

**User's choice:** Dedicated db.py helper

---

## Hot-reload Propagation

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite config_version table (Recommended) | Separate table, single version INTEGER row, survives restarts | ✓ |
| In-memory counter | Python global, resets on restart | |
| Updated_at column | Use max(updated_at) as version signal | |

**User's choice:** SQLite config_version table

| Option | Description | Selected |
|--------|-------------|----------|
| Observer registry (Recommended) | ConfigLoader.on_change(key, callback) invoked synchronously after cache refresh | ✓ |
| Global list + periodic check | Components poll their own interval | |
| Broadcast to all | All callbacks invoked on any change | |

**User's choice:** Observer registry

| Option | Description | Selected |
|--------|-------------|----------|
| Decorator + registration (Recommended) | @config.on_change('KEY') pattern | ✓ |
| Manual registration | config.register_hook('KEY', callback) | |

**User's choice:** Decorator + registration

| Option | Description | Selected |
|--------|-------------|----------|
| Catch and log (Recommended) | Each hook wrapped in try/except, logged errors | ✓ |
| Fail-fast | Exception propagates, blocks all hooks | |

**User's choice:** Catch and log

---

## the agent's Discretion

- Seed key list for initial SQLite population
- Config table index strategy
- Log verbosity for config operations

## Deferred Ideas

None — discussion stayed within phase scope.
