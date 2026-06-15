# Phase 40: Configuration Backlog - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Database-backed configuration system: layered config loader (SQLite → `.env` → `os.getenv` defaults), REST CRUD API for reading/updating config, and hot-reload event bus that notifies components when config changes.

Requirements: CONF-01, CONF-02, CONF-03, CONF-04, CONF-05, CONF-06, CONF-07, CONF-08

</domain>

<decisions>
## Implementation Decisions

### ConfigLoader Design
- **D-01:** ConfigLoader replaces inline `os.getenv()` calls across the codebase. `ConfigLoader.get(key, default)` is the single source of truth — chain: SQLite → `.env` → `os.getenv` default.
- **D-02:** Silent degradation when SQLite unavailable — log a warning, fall through to `.env` → `os.getenv` default (CONF-08 compliant). Never hard-fail.
- **D-03:** Early bootstrap timing: ConfigLoader loads SQLite values during `bootstrap_env()`, after `dotenv` loads `.env` but before any service code runs. `ConfigLoader.get()` reads the in-memory cache dynamically per call.
- **D-04:** In-memory dict cache with version counter. Fast reads; version mismatch triggers cache refresh.

### API Server Placement
- **D-05:** Config REST API mounted on the health server (port 8000) — reuses the existing FastAPI app in `kb_server/health_server.py`. No new server process.
- **D-06:** Fixed endpoint path: `/api/v1/config`. Not configurable.
- **D-07:** No auth on config API initially — matches the health server's existing no-auth pattern. Auth gap will be filled when Phase 28b (Auth API) ships.

### Type Validation
- **D-08:** Supported config value types: `string`, `int`, `float`, `bool`, `json`, `list`.
- **D-09:** Validation errors return HTTP 422 with field-level error detail: `{"error": "Validation failed", "field": "value", "type": "int", "reason": "..."}`.
- **D-10:** PUT upserts — creates the config key if it doesn't already exist.
- **D-11:** `group` and `description` are required in the PUT request body for new key creation.

### Database & Connection Management
- **D-12:** ConfigLoader uses its own SQLite connection pool to `kb_metadata.db` — independent of the query_logger's connection.
- **D-13:** Auto-create the `config` table via `CREATE TABLE IF NOT EXISTS` during startup. No manual migration step.
- **D-14:** Enable WAL mode (`PRAGMA journal_mode=WAL`) on the `kb_metadata.db` connection. This is also the AUTH-14 prerequisite — setting up concurrent-read capability for Phase 28b.
- **D-15:** Dedicated `kb_server/config/db.py` helper with `get_connection(db_path)` context manager. Reusable by other components and serves as the `db_utils.py` concept for AUTH-14.

### Hot-reload Propagation
- **D-16:** SQLite `config_version` table (single row: `version INTEGER`) for version-based change detection. Bumped on every PUT/reset. Survives restarts.
- **D-17:** Observer registry (not polling): `ConfigLoader.on_change(key_or_pattern, callback)`. After cache refresh on version mismatch, matching callbacks are invoked synchronously.
- **D-18:** Decorator registration: `@config.on_change("MCP_PORT")` style. Registered during module init.
- **D-19:** Hook errors are caught and logged — one failing hook does not block other hooks from receiving the update.

### the agent's Discretion
- Seed key list for initial SQLite population — agent decides which subset of known `os.getenv()` keys to seed on first startup.
- Config table index strategy — agent decides if indexes on `group` or `updated_at` are needed.
- Log verbosity for config operations — agent chooses appropriate log levels.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Implementation Files
- `kb_server/server.py` — Existing MCP server with ~30+ `os.getenv()` calls that ConfigLoader will replace. The bootstrap_env() call at line 22 is where ConfigLoader hooks in.
- `config/bootstrap_env.py` — Existing `.env` loader. ConfigLoader loads AFTER this runs but BEFORE service code.
- `kb_server/health_server.py` — Existing FastAPI app on port 8000. Config REST API mounts here.
- `observability/metrics.py` — Prometheus metrics functions. ConfigLoader hooks may need to trigger metric reload on config change.
- `kb_server/telemetry/query_logger.py` — Existing SQLite usage in `kb_metadata.db`. ConfigLoader uses the same database but its own connection.

### Planning Artifacts
- `.planning/ROADMAP.md` §Phase 40 — Phase goal, success criteria, requirement mapping.
- `.planning/REQUIREMENTS.md` §Config API — CONF-01 through CONF-08 requirement definitions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config/bootstrap_env.py` — Existing `load_dotenv()` + env setup. ConfigLoader extends this to add SQLite layer after dotenv load.
- `kb_server/health_server.py` — FastAPI app with Starlette routes. Config API routes will be mounted as an APIRouter here.
- Existing SQLite patterns in `ingest/core/metadata.py` and `kb_server/telemetry/query_logger.py` — reference for `kb_server/config/db.py` connection management.

### Established Patterns
- **Env var config**: `os.getenv("VAR_NAME", default)` pattern used across ~30+ call sites in `server.py` and other modules. ConfigLoader.get() replaces these.
- **Bootstrap sequence**: `bootstrap_env()` at module top, called early in startup. ConfigLoader integrates into this sequence.
- **Prometheus metrics**: `prometheus_client` Gauge/Counter with `transport` label. ConfigLoader may add `config_version` gauge.
- **FastAPI health server**: Starlette `Route` objects on port 8000. Config API adds routes in the same style.

### Integration Points
- `kb_server/server.py:21-22` — `from config.bootstrap_env import bootstrap_env` / `bootstrap_env()`. ConfigLoader integration point.
- `kb_server/health_server.py:17-18` — Same bootstrap call. Config router mounts here.
- `config/bootstrap_env.py` — After `load_dotenv()`, insert ConfigLoader init and table creation.
- All server.py module-level config reads (lines 60-96) — eventual migration targets for ConfigLoader.get().

</code_context>

<specifics>
## Specific Ideas

- Config table seeding: populate known env var keys into the config table on first run so the REST API shows all configurable values from the start. Agent decides which keys to include.
- Version gauge: expose `kb_rag_config_version` Prometheus gauge for monitoring config change frequency.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 40-config-backlog*
*Context gathered: 2026-06-15*
