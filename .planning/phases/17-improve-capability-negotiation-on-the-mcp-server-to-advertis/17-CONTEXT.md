# Phase 17: Improve capability negotiation on the MCP server to advertise classified attributes - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Advertise OTCS auto-tagging attributes (vendor, product, subsystem, module, version) during MCP tool negotiation so clients can discover available filter values. Uses a three-layer approach: dynamic tool descriptions listing top-N values, a new `list_filter_options` tool for full enumeration, and unbounded string parameters (no enum constraints). Maintains a compact terms table indexed from the knowledge base — token-size controlled to avoid excessive context consumption.

</domain>

<decisions>
## Implementation Decisions

### Injection Point (Three-Layer Hybrid)
- **D-01:** Layer 1 — **Dynamic tool descriptions** append top-N available values to `search_kb` and `list_documents` parameter descriptions. E.g., "Filter by product. Available: AppServer, DataSync, AdminPortal,... (+12 more)"
- **D-02:** Layer 2 — **No enum constraints** on `product`, `vendor`, `subsystem`, `module`, `version` parameters. Keep as unbounded strings. The enum constraint is a hard schema contract; truncation would falsely exclude valid values. Existing `doc_type` and `filter_type` enums remain unchanged.
- **D-03:** Layer 3 — **New MCP tool** `list_filter_options` for full value enumeration when clients need the complete list.

### New Tool: list_filter_options
- **D-04:** **Name:** `list_filter_options` — follows existing `list_` prefix pattern (cf. `list_collections`, `list_documents`).
- **D-05:** **Parameters:** `field` (optional string — if omitted, returns all fields), `collection` (optional string — for multi-collection setups). Follows existing tool parameter conventions.
- **D-06:** **Returns:** Available distinct values for the requested field(s) in the target collection, with counts per value.

### Truncation Strategy
- **D-07:** **Top-N = 20** — tool descriptions show the 20 most common values per attribute, with "(+N more)" suffix when truncated.
- **D-08:** The `list_filter_options` tool returns ALL values — no truncation.

### Value Source & Refresh
- **D-09:** **Startup scan + event-driven refresh.** On server startup, scan Qdrant to build the terms table (cached in memory).
- **D-10:** **Cache-bust marker file** — the ingest pipeline writes a `.filter_cache_bust` file with timestamp after each successful ingest/reclassify run. The server checks this file's mtime on `list_tools()`; if newer than last scan, re-indexes the terms table.
- **D-11:** `list_tools()` itself remains fast — the check is a lightweight mtime comparison; re-indexing only happens when the marker changed.

### Module Attribute
- **D-12:** **Add "module" as a new classification axis.** Extends `classifier.py` with `infer_module()` and associated patterns. Adds `module` to Qdrant chunk payload (via `ingest.py`). Adds `module` filter parameter to `search_kb` and `list_documents` tools (via `server.py`). The `list_filter_options` tool then advertises available module values.

### Attributes in Scope
- **D-13:** Attributes to advertise: `vendor`, `product`, `doc_type`, `subsystem`, `module`, `version`, `filter_type`. (doc_type and filter_type already have static enums — description will be augmented with available values.)

### the agent's Discretion
- Exact description format for top-N values in tool descriptions
- Exact return format of `list_filter_options` (markdown text or structured text)
- Cache-bust marker file naming convention and contents
- Implementation of `infer_module()` in classifier.py (pattern matching approach)
- Qdrant payload schema changes for the `module` field
- Error handling for `list_filter_options` (unknown field, empty collection)
- Whether to include counts ("12 documents") in description or just value names
- Whether `list_filter_options` returns values in frequency order or alphabetical

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §"Phase 17" — CAPNEG-01 through CAPNEG-04 requirements
- `.planning/ROADMAP.md` §"Phase 17" — Phase 17 goal, depends-on, plan stubs

### MCP Server Layer (core target)
- `kb_server/server.py` — MCP tool definitions. `list_tools()` at line 84 returns 5 Tool objects with inputSchema. All tool parameters and descriptions defined here. This is the primary file to modify for dynamic descriptions and the new `list_filter_options` tool.

### Classification System (module attribute)
- `ingest/classifier.py` — Classification pipeline: `classify()` returns dict with product/doc_type/vendor/subsystem/version. Module inference logic will be added here. 865 lines.
- `ingest/ingest.py` — Ingest orchestrator; stores classification results in Qdrant chunk payload. Lines 410-459 show payload structure.

### Vector Store & Registry
- `kb_server/vector_store.py` — `VectorStore` class with async Qdrant operations. `search()` and `list_documents()` accept filter parameters. New `get_distinct_values()` method may be needed for terms table indexing.
- `ingest/registry.py` — `IngestRegistry` SQLite tracking. Cache-bust marker file interaction could optionally go through registry.

### Prior Phase Context
- `.planning/phases/11-auto-classification/11-SUMMARY.md` — Phase 11 deliverables: vendor/subsystem inference, metadata extraction. Context for existing classification.
- `.planning/phases/16-reclassification-ingested-docs/16-CONTEXT.md` — Reclassification adds metadata update capability. Relevant for ensuring module field is reclassifiable.

### Project Constraints
- `.planning/PROJECT.md` — No new dependencies, CLI backward-compatible, test baseline 585+ (no regressions), English-only, TDD mandatory for behavior changes.
- `.planning/codebase/STACK.md` — Dependencies: `mcp==1.27.1`, `qdrant-client==1.18.0`, `pydantic==2.13.4`. All needed libraries already in stack.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`kb_server/server.py:list_tools()`** (line 84) — Returns 5 Tool definitions. The `search_kb` and `list_documents` tools have static description strings with hardcoded examples. These descriptions will become dynamic, pulling top-N values from the terms cache.
- **`kb_server/server.py:_search_kb()`** (line 372) — Accepts product/doc_type/version/vendor/subsystem/filter_type parameters. Passes them as Qdrant filters. Module parameter will be added here.
- **`ingest/classifier.py:classify()`** (line 757) — Returns dict with product/doc_type/vendor/subsystem/version. `infer_module()` needs to be added and the result dict extended.
- **`ingest/classifier.py:infer_subsystem()`** (line 458) — Pattern for `infer_module()` — directory-based inference with pattern tables.

### Established Patterns
- **MCP tool definitions:** Tools registered via `@app.list_tools()` decorator returning list of `types.Tool(name, description, inputSchema)`. All parameters are flat dict with type/description/default.
- **Static description strings:** Currently hardcoded with example values. Will become dynamic via string interpolation from the terms cache.
- **No new dependencies allowed:** Everything must use mcp 1.27.1's existing capabilities (Tool description + inputSchema — no custom MCP extensions).
- **Async throughout:** All tool handlers are async (`_search_kb`, `_list_documents`, etc.). Terms cache operations must be async.
- **Logger naming:** `log = logging.getLogger("kb-mcp")` pattern.
- **Collection router:** `CollectionRouter.resolve()` handles collection parameter resolution. New `list_filter_options` tool should use the same pattern.

### Integration Points
- **`kb_server/server.py`** — Add `module` to `search_kb` inputSchema (line 165 area) and `_search_kb()` parameter extraction (line 380 area). Add same to `list_documents`.
- **`ingest/classifier.py`** — Add `infer_module()` function, `MODULE_PATTERNS` table, extend `classify()` result.
- **`ingest/ingest.py`** — Add `module` to chunk payload stored in Qdrant (line 459 area).
- **`ingest/registry.py` or ingest pipeline** — Write `.filter_cache_bust` marker after successful ingest/reclassify.
- **`kb_server/vector_store.py`** — May need `get_distinct_values(collection, field)` method for terms table scanning.
- **Cache layer** — Terms table lives in memory (not disk cache). Simple dict or LRU-like structure.

### Targeting Identified
- `server.py` list_tools() descriptions must become dynamic — currently static strings that include hardcoded examples like "Examples: AppServer, DataSync, AdminPortal, Adobe, SAP, ISO, general"
- `classifier.py` needs new `infer_module()` — follow `infer_subsystem()` pattern
- Qdrant payload schema needs `module` field added

</code_context>

<specifics>
## Specific Ideas

- Dynamic description format example: `"Filter by product. Common values: AppServer (142 docs), DataSync (89 docs), AdminPortal (45 docs)... (+12 more)"`
- `list_filter_options` return format (markdown): `## Filter Options\n**product** (12 values): AppServer, DataSync, AdminPortal...`
- New tool receives `field` param for single-field query, or no params for all-fields dump
- Module inference: likely from directory structure patterns (like subsystem), potentially from filename patterns too
- Cache-bust file path: `data/.filter_cache_bust` — simple timestamp file written by ingest pipeline

</specifics>

<deferred>
## Deferred Ideas

- Adding `enum` constraints to product/vendor/subsystem/module/version (rejected — would create false-negative validation)
- `--analyze` mode for `list_filter_options` showing frequency distributions (out of scope; belongs in analytics phase)
- Real-time Qdrant change detection via watch/trigger (event-driven via marker file is sufficient)

</deferred>

---

*Phase: 17-Improve-Capability-Negotiation*
*Context gathered: 2026-05-27*
