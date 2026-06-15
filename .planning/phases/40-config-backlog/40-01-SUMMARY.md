# Plan 40-01 SUMMARY: Config Table, ConfigLoader & REST API

## Objective

Add a SQLite-backed config storage table with a ConfigLoader class that wraps os.getenv with SQLite override chain, and expose CRUD operations through a FastAPI REST router at /api/v1/config.

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/test_config_api.py -x -v` | ✅ 21/21 PASS |
| `flake8 kb_server/config/ tests/test_config_api.py` | ✅ Clean |
| `black --check kb_server/config/ tests/test_config_api.py` | ✅ Clean |
| `isort --check-only kb_server/config/ tests/test_config_api.py` | ✅ Clean |
| `mypy kb_server/config/` | ✅ No issues |

## Tasks Executed

| # | Task | Status |
|---|------|--------|
| 1 | Config table schema + ConfigLoader with CRUD + env fallback | ✅ |
| 2 | Config REST API router with full CRUD and reset endpoints | ✅ |

## Key Files Created

- `kb_server/config/__init__.py` — Empty package init
- `kb_server/config/db.py` — SQLite connection context manager, config table schema, version tracking
- `kb_server/config/models.py` — Type conversion (`TYPE_MAP`), validation (`validate_type`)
- `kb_server/config/loader.py` — `ConfigLoader` class: `get()`/`set()`/`delete()`/`get_all()`/`reset_all()`/`on_change()`, env fallback chain, observer registry
- `kb_server/config/router.py` — FastAPI `APIRouter` at `/api/v1/config`: GET/PUT/DELETE per-key + POST /reset, 422 type validation, 404 for missing keys
- `tests/test_config_api.py` — 21 tests covering ConfigLoader CRUD, typed values, env fallback, validation errors, REST API endpoints, group filtering, upsert

## Implementation Notes

- Config table created in `kb_metadata.db` with `config` (key/value/type/group/description/timestamps) and `config_version` (single-row version counter) tables
- ConfigLoader resolves values via chain: SQLite → `.env` file → `os.getenv` defaults (D-03)
- Silent degradation when SQLite unavailable — logs warning, falls through to env (D-02, CONF-08)
- In-memory dict cache with version counter for fast reads (D-04)
- Observer registry with `on_change(key, callback)` for hot-reload propagation (D-17/D-18)
- Supported types: string, int, float, bool, json, list (D-08)
- Dedicated `kb_server/config/db.py` connection helper with WAL mode (D-14/D-15)
- Config API designed to mount on the health server FastAPI app (D-05) — requires `app.state.config_loader = ConfigLoader()` injection
