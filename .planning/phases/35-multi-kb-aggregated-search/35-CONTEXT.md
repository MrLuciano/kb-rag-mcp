# Phase 35: Multi-KB Aggregated Search

**Status:** Backlog (promoted from ROADMAP.md)
**Priority:** Medium
**Code:** MULTIKB-01
**Competitive Reference:** [kalicyh/mcp-rag](https://github.com/kalicyh/mcp-rag) — multi-KB aggregated search
**Promoted from:** `.planning/ROADMAP.md` Backlog (Medium Priority)

## Objective

Add `kb_ids` parameter on `search_kb` to search across multiple knowledge bases in a single query, merging and deduplicating results by score. Enables a unified view across all indexed content.

## Expected Deliverables

- `kb_ids: list[str]` parameter on `search_kb` MCP tool
- Parallel search against multiple Qdrant collections
- Score normalization across collections (different embedding models may produce different score ranges)
- Deduplication by chunk content (same content in multiple KBs appears once)
- Result ranking using RRF (Reciprocal Rank Fusion) across collections
- Filter propagation to sub-queries (module, vendor, doc_type filters apply across all KBs)

## Search Algorithm

1. Parse `kb_ids` — if empty, fall back to single-KB search (backward compatible)
2. For each `kb_id`, resolve to Qdrant collection via `CollectionRouter`
3. Execute search on all collections in parallel (using asyncio.gather)
4. Collect results, normalize scores (min-max scaling to [0, 1] per collection)
5. Merge normalized result lists using RRF fusion
6. Deduplicate by `chunk_id` (if same content indexed in multiple KBs, keep highest score)
7. Return top-k merged results

## Key Design Decisions

- **Collection resolution:** `CollectionRouter.resolve_kb_id(kb_id)` already exists (from Phase 27)
- **Score normalization:** Use min-max scaling per collection so RRF isn't biased toward higher-score collections
- **Deduplication:** Use `chunk_id` as dedup key (each chunk is unique across collections)
- **Fallback:** If `kb_ids` contains an invalid ID, return error (fail fast — don't silently skip)
- **Empty `kb_ids`:** Defaults to current single-KB behavior (backward compatible with existing callers)

## Implementation Scope

1. Update `search_kb` handler in `kb_server/server.py` to accept `kb_ids: Optional[list[str]]`
2. Add multi-collection search in `kb_server/vector_store.py` (new `multi_search` method)
3. Add score normalization and RRF fusion in `kb_server/retrieval/hybrid_search.py`
4. Add deduplication step before returning results
5. Update MCP tool description to document `kb_ids` parameter

## Open Questions

1. Should we support `kb_ids` with wildcard (search ALL KBs the caller has access to)?
2. How to handle different embedding dimensions across KBs (cross-collection search requires same dimension)?
3. Should the result indicate which KB each result came from (for UI display)?

## See Also

- `kalicyh/mcp-rag` multi-KB search (GitHub: kalicyh/mcp-rag)
- `kb_server/collections/router.py` — existing `resolve_kb_id()` from Phase 27
- `kb_server/retrieval/hybrid_search.py` — existing RRF fusion implementation
- `kb_server/server.py` — `search_kb` handler