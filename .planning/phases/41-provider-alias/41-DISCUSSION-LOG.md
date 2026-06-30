# Phase 41: Provider Alias - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 41-provider-alias
**Areas discussed:** Hot-reload mechanism, Alias naming & storage format, Integration point in EmbedClient, Scope

---

## Hot-reload Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Use existing observer model | Register on_change('provider_alias.*', callback) with Phase 40's version-based system. No new watcher class needed. | ✓ |
| Add separate mtime polling | Dedicated ConfigWatcher that polls SQLite mtime. Redundant with Phase 40's system but explicit. | |
| You decide | Agent chooses the best approach based on existing infrastructure. | |

**User's choice:** Use existing observer model (Recommended)
**Notes:** Phase 40 already has version-based change detection (D-17). No need for redundant polling.

---

## Alias Naming & Storage Format

| Option | Description | Selected |
|--------|-------------|----------|
| One flat group (Recommended) | All aliases in group='provider_alias'. ConfigLoader.get_all(group='provider_alias') returns them all. | ✓ |
| Per-backend groups | Separate groups like 'provider_alias.lmstudio', 'provider_alias.ollama'. More organized but harder to enumerate. | |
| You decide | Agent picks based on simplicity. | |

**User's choice:** One flat group (Recommended)
**Notes:** Simple enumeration via get_all(group='provider_alias').

---

## Integration Point in EmbedClient

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy on each call (Recommended) | Resolve alias inside _get_provider_url() / _select_backend() on each EmbedClient call. Works with hot-reload. | ✓ |
| At service init / bootstrap | Resolve alias once during bootstrap_env(), after ConfigLoader initializes. Stale until restart. | |
| You decide | Agent picks best approach. | |

**User's choice:** Lazy on each call (Recommended)
**Notes:** Keeps hot-reload live since config cache is checked each call.

---

## Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Provider name only (Recommended) | Aliases map provider short names only. Handles PROV-01 and PROV-02. | ✓ |
| Provider name + URL | Aliases could also override URLs and model names. | |
| You decide | Picks based on requirements scope. | |

**User's choice:** Provider name only (Recommended)
**Notes:** Keeps scope tight. URLs/model names already covered by existing env vars.

---

## the agent's Discretion

- Exact code path in EmbedClient where alias resolution is injected
- Whether to use on_change wildcard hook or iterate get_all with prefix matching
- Error handling approach for missing aliases
- Test strategy

## Deferred Ideas

None — discussion stayed within phase scope.
