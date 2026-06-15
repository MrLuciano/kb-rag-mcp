# Phase 41: Provider Alias - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Configurable provider name aliases for multi-backend embedding resolution with hot-reload. Admin defines aliases via config entries (group `provider_alias`, key pattern `provider_alias.<canonical_name>`). EmbedClient reads aliases on resolution and falls back to value-as-is if no alias found.

Requirements: PROV-01, PROV-02

</domain>

<decisions>
## Implementation Decisions

### Alias Storage Format
- **D-01:** Flat structure — all aliases stored in config table with `group_name = 'provider_alias'`, key pattern `provider_alias.<canonical_name>` (e.g., `provider_alias.aliyun`), value = canonical provider name. Enumerate via `ConfigLoader.get_all(group='provider_alias')`.

### Integration with EmbedClient
- **D-02:** Lazy alias resolution per call — alias is resolved at provider-selection time inside `_get_provider_url()` / backend resolution path, not at module import time. This keeps hot-reload live since the config cache is checked each call.

### Hot-reload
- **D-03:** Reuse Phase 40's existing observer model — register `on_change("provider_alias.*", callback)` on the ConfigLoader. No separate polling or file-watch class needed. When alias entries change, the observer triggers a cache refresh that takes effect on the next EmbedClient call.

### Scope
- **D-04:** Provider name aliases only — maps short names to canonical names (e.g., `"aliyun"` → `"dashscope"`). Does NOT map URLs, API keys, or model names. Those remain configured via existing env vars and config entries.

### the agent's Discretion
- Exact code path in EmbedClient where alias resolution is injected (provider chain parsing or backend selection).
- Whether to use `on_change` wildcard hook or iterate `get_all` with prefix matching.
- Error handling: log warning and fall back to value-as-is when alias key doesn't exist or maps to an unknown provider.
- Test strategy: unit tests for resolve logic + config entry CRUD tests.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Config System (Phase 40 — dependency)
- `.planning/phases/40-config-backlog/40-CONTEXT.md` — ConfigLoader API, observer registry (D-17), version-based change detection
- `kb_server/config/loader.py` — ConfigLoader class with `on_change()`, `get()`, `get_all()`
- `kb_server/config/db.py` — Config table schema (group_name, key, value, type)

### Embedding Client
- `kb_server/embed_client.py` — Module-level BACKEND, provider chain parsing, _resolve_backend flow

### Requirements & Roadmap
- `.planning/ROADMAP.md` §Phase 41 — Phase goal, success criteria
- `.planning/REQUIREMENTS.md` §Provider Aliases — PROV-01, PROV-02 definitions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ConfigLoader.on_change(key_or_pattern, callback)` — Observer registry for hot-reload. Supports wildcard patterns (Phase 40 D-17, D-18).
- `ConfigLoader.get_all(group_name=...)` — Enumerate all config entries in a group. Used to discover all defined aliases.
- Provider chain parsing in `embed_client.py:51-54` — `PROVIDER_CHAIN = [p.strip() for p in BACKEND.split(";")]` — this is where alias resolution could integrate.

### Established Patterns
- **Phase 40 ConfigLoader**: Synchronous SQLite with version-based cache invalidation. All config reads go through `get()` with env fallback.
- **Provider resilience**: Circuit breaker + budget tracking wraps each provider — alias resolution happens before these layers in the call chain.

### Integration Points
- `kb_server/embed_client.py:41-54` — BACKEND and PROVIDER_CHAIN are module-level. Alias resolution should happen when these are consumed, not at import time (D-02).

</code_context>

<specifics>
## Specific Ideas

- Alias examples: `provider_alias.aliyun=dashscope`, `provider_alias.my-local=lmstudio-rest`
- Resolution should log a debug message when an alias resolves: `"Provider alias resolved: aliyun → dashscope"`
- Missing alias warning logged only once per key (avoid log spam on every request)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 41-provider-alias*
*Context gathered: 2026-06-15 via discuss-phase*
