# Phase 17: Improve capability negotiation on the MCP server to advertise classified attributes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 17-Improve-Capability-Negotiation
**Areas discussed:** Injection point, Truncation strategy, Enum strategy, New tool design, Refresh strategy, Change detection, Top-N limit, Module vs subsystem

---

## Injection Point

| Option | Description | Selected |
|--------|-------------|----------|
| Inside tool descriptions | Append available values to existing tool descriptions | |
| InputSchema enums | Add enum constraints like doc_type already has | |
| New tool | Add `get_filter_options()` or similar | |
| Hybrid — descriptions first | Start with descriptions, evolve later | |
| Hybrid — all three | Descriptions list top values, no enums, separate tool for full list | ✓ |

**User's choice:** Hybrid — all three
**Notes:** Descriptions for discoverability, no enums (keeps schema contract unbounded), separate tool for full enumeration.

---

## Truncation Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Truncate to top-N everywhere | Description, enum, tool all show top-N | |
| Top-N for description+enum, full in separate tool | Description and enum truncated, tool full | ✓ |
| Full lists everywhere | No truncation | |

**User's choice:** Top-N for description+enum, full in separate tool
**Notes:** However, enums were later removed from consideration (see next area), so this applies only to descriptions.

---

## Enum Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Keep enums out | Description for discoverability, separate tool for full list | ✓ |
| Truncate enums | Accept trade-off that some valid values would be schema-invalid | |
| Full enum | All values in enum, accept potentially large schema | |

**User's choice:** Keep enums out — descriptions for discoverability, separate tool for full list
**Notes:** User noted "most of the values are already filters to the data, use option 1 and a separate tool full list". This avoids the schema contract problem where truncation would falsely exclude valid values.

---

## New Tool Design

| Option | Description | Selected |
|--------|-------------|----------|
| No params | Returns all values for all attributes | |
| Filter by attribute | Accepts attribute param, returns that attribute's values | |
| Filter by attribute + collection | Accepts attribute and collection params | |
| Named `list_filter_options` | Same as above, but follows existing `list_` naming pattern | ✓ |

**User's choice:** Named `list_filter_options`
**Notes:** Follows existing `list_collections`, `list_documents` pattern.

---

## Refresh Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Startup scan + memory cache | Scan on startup, stale until restart | |
| Lazy — scan on list_tools() | Always fresh, slower startup | |
| Startup + periodic refresh | Background task | |
| Startup + event-driven refresh | Cache invalidation on data change | ✓ |

**User's choice:** Startup + event-driven refresh

---

## Change Detection

| Option | Description | Selected |
|--------|-------------|----------|
| Qdrant point count diff | Lightweight check | |
| Registry file mtime | Watch data/registry.db | |
| Cache-bust marker file | Ingest writes marker, server checks mtime | ✓ |
| Short TTL (30s) + startup | Simplest TTL-based approach | |

**User's choice:** Cache-bust marker file
**Notes:** Ingest pipeline writes `.filter_cache_bust` file after each successful run. Server checks mtime on `list_tools()`.

---

## Top-N Limit

| Option | Description | Selected |
|--------|-------------|----------|
| 10 | Show top 10 values per attribute | |
| 20 | Show top 20 values per attribute | ✓ |

**User's choice:** 20

---

## Module vs Subsystem

| Option | Description | Selected |
|--------|-------------|----------|
| Subsystem only (no module) | Module = subsystem for this phase | |
| Add module as new attribute | In Phase 17 scope | ✓ |

**User's choice:** Add module as new attribute
**Notes:** User wants "module" as a separate classification axis, distinct from subsystem. Requires extending classifier.py with `infer_module()`, updating Qdrant payload, and adding module filter to MCP tools.

---

## the agent's Discretion

- Exact description format for top-N values in tool descriptions
- Exact return format of `list_filter_options` (markdown text or structured text)
- Cache-bust marker file naming convention and contents
- Implementation of `infer_module()` in classifier.py
- Qdrant payload schema changes for the `module` field
- Error handling for `list_filter_options`
- Whether to include document counts in descriptions
- Whether `list_filter_options` returns values in frequency order or alphabetical

## Deferred Ideas

- Adding enum constraints to product/vendor/subsystem/module/version (rejected)
- `--analyze` mode for `list_filter_options` (out of scope)
- Real-time Qdrant change detection via watch/trigger (marker file is sufficient)
