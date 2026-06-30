# Phase 43: Chunk Preview in Document Detail - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Inline chunk viewer in the existing `/ui/document/{id}` page showing all chunks for a document with expandable accordion, text content, and server-side search term highlighting.

Requirements: SPA-03

</domain>

<decisions>
## Implementation Decisions

### Display Format
- **D-01:** Bootstrap accordion — each chunk is a collapsed accordion item showing a text snippet. Click to expand and read full chunk text. Compact, fits the existing Bootstrap 5 UI.

### Search Term Highlighting
- **D-02:** Server-side `<mark>` tag wrapping — pass search query via `?q=terms` URL param. Backend wraps matched terms in `<mark>` before rendering. No JavaScript required. Case-insensitive matching.

### Integration Point
- **D-03:** Enhance existing `/ui/document/{id}` route to also query Qdrant for chunks and pass them to the template. Single-page experience — metadata card + chunk accordion below. No additional endpoints needed.

### Chunk Metadata
- **D-04:** Chunk text content only displayed per chunk. Chunk sequence index shown as accordion header label ("Chunk 1", "Chunk 2", etc.). No scores, counts, or other metadata on individual chunks.

### Pagination
- **D-05:** Render all chunks, first 10 visible with accordion expanded. Remaining chunks start collapsed. "Show next 10" button at bottom loads next batch. Works with HTMX partial loading for progressive reveal.

### the agent's Discretion
- Qdrant scroll query implementation details (batch size, field selection, pagination cursor)
- Whether to use VectorStore.scroll() or direct Qdrant client call
- Exact `<mark>` wrapping implementation (regex vs simple string replace)
- Error handling when Qdrant is unreachable

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Document Detail
- `kb_server/ui/templates/document.html` — Existing template to enhance with chunk accordion
- `kb_server/ui/routes.py:187-212` — Existing `document_detail` route handler to extend
- `kb_server/ui/routes.py:15-24` — `_map_document()` helper

### Qdrant Chunk Access
- `kb_server/vector_store.py` — VectorStore with scroll, search, get_chunk methods
- `kb_server/retrieval/reranker.py` — Chunk payload structure reference

### Admin SPA (dependency)
- `.planning/phases/28c-admin-spa-panel/28c-CONTEXT.md` — Admin SPA patterns
- `kb_server/ui/templates/base.html` — Base template, Bootstrap 5 accordion component

### Requirements
- `.planning/ROADMAP.md` §Phase 43 — Phase goal, success criteria
- `.planning/REQUIREMENTS.md` — SPA-03 definition

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `VectorStore` class — Has `scroll()` method to retrieve all chunks for a collection. Can filter by source_file.
- Existing document route — `/ui/document/{id}` already renders metadata. Adding chunk data is an extension.
- Bootstrap 5 accordion component — Available via CDN, no extra dependency.

### Established Patterns
- **Server-rendered HTML**: All UI templates use Jinja2 server-side rendering. Chunk accordion follows this pattern.
- **HTMX progressive loading**: "Show next 10" button uses `hx-get` pattern similar to the analytics tab refresh.

### Integration Points
- `kb_server/ui/routes.py:210` — Template context — add `chunks` and `search_query` to the response
- `kb_server/vector_store.py` — `scroll()` method to fetch chunks by source_file filter

</code_context>

<specifics>
## Specific Ideas

- Accordion header shows "Chunk N" with first ~50 chars of text as preview
- Search term highlighting: `highlight_term(text, query)` Jinja2 filter or template function
- Empty state: "No chunks found for this document" when Qdrant returns empty
- Qdrant error: "Chunks unavailable (Qdrant connection error)" with degraded experience — metadata still shows
- "Show next 10" button replaced with "Show less" when all chunks are visible

</specifics>

<deferred>
## Deferred Ideas

- Score/vector distance display in chunks — deferred, text-only for now
- Full metadata view (word count, tokens) — deferred
- Separate chunk detail page — deferred, accordion is sufficient
- Client-side highlighting — deferred, server-side covers the primary use case

</deferred>

---

*Phase: 43-chunk-preview-document-detail*
*Context gathered: 2026-06-15 via discuss-phase*
