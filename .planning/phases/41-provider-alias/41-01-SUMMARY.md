# Plan 41-01 SUMMARY: Provider Alias

## Objective

Add provider alias resolution to ConfigLoader so embed_client.py can resolve friendly names (e.g., "aliyun" → "dashscope") through config entries, with lazy per-call resolution and hot-reload via Phase 40's observer model.

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/test_provider_alias.py -v` | ✅ 14/14 PASS |
| `pytest tests/test_config_api.py -v` | ✅ 21/21 PASS (no regressions) |
| `pytest tests/test_embed_client_unit.py -v` | ✅ 15/15 PASS (no regressions) |
| `flake8 kb_server/config/loader.py tests/test_provider_alias.py` | ✅ Clean |
| `black --check kb_server/config/loader.py kb_server/embed_client.py tests/test_provider_alias.py` | ✅ Clean |

## Tasks Executed

| # | Task | Status |
|---|------|--------|
| 1 | ConfigLoader: get_aliases(), resolve_alias(), wildcard observer support | ✅ |
| 2 | EmbedClient: lazy alias resolution in _try_provider + init_alias_resolution + tests | ✅ |

## Files Modified

- `kb_server/config/loader.py` — Added `get_aliases()` (enumerate all aliases as dict), `resolve_alias()` (single alias lookup), enhanced `_notify_observers` with `prefix.*` wildcard matching
- `kb_server/embed_client.py` — Added `_config_loader` module variable, `init_alias_resolution()`, `_resolve_alias()` function, lazy alias resolution in `_try_provider()`, alias-aware `validate_providers()`
- `tests/test_provider_alias.py` — 14 tests covering ConfigLoader methods, wildcard observer backward compat, EmbedClient integration

## Implementation Notes

- ConfigLoader methods follow existing patterns: `_refresh_cache()`, try/except with log.warning, return safe defaults
- Alias resolution is lazy per-call (D-02) — no cached aliases at module level
- Wildcard observer is backward-compatible: `prefix.*` matching uses `key.startswith(pattern[:-2])`, existing exact-match and `*` observers unchanged (D-03)
- EmbedClient injects alias resolution before `_BACKENDS.get(provider)` in `_try_provider` — if the raw provider name isn't found in `_BACKENDS`, it resolves as alias before retrying
- Hot-reload hook: `init_alias_resolution()` registers `on_change("provider_alias.*", callback)` — alias changes take effect on the next EmbedClient call
