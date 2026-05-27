---
id: 17-01
phase: 17
status: complete
completed: 2026-05-27
task_count: 11
commits:
  - 9de51c1 feat(classifier): add infer_module() with MODULE_PATTERNS table
  - 3541e8d feat(ingest): integrate module field into classify() and chunk payload
  - 537e6e4 feat(server): add module filter to search_kb, list_documents, VectorStore
  - e48b40d feat(reclassify): add module field to reclassification scope
  - c25b2aa feat(store): add get_distinct_values() for terms table scanning
  - 018630c feat(cache): add FilterTermsCache with cache-bust marker refresh
  - 2b44c14 feat(pipeline): write filter cache-bust marker after ingest/reclassify
  - ee7c102 feat(server): dynamic list_tools() descriptions with top-20 filter values
  - 5c96d6b feat(server): register and implement list_filter_options tool
  - ae66280 test: add integration smoke test for list_filter_options
---

# Plan 17-01: Capability Negotiation — Summary

## What was built

Three-layer capability negotiation for MCP attribute advertisement:

### Plan 17-01: Module Classification Axis
- `infer_module()` with `MODULE_PATTERNS` in `ingest/classifier.py`
- Module field integrated into `classify()` output and Qdrant chunk payload
- Module filter support in `search_kb`, `list_documents`, and `VectorStore`
- Module field added to reclassification scope

### Plan 17-02: Terms Table & Dynamic Descriptions
- `FilterTermsCache` singleton in `kb_server/filter_terms_cache.py`
- `get_distinct_values()` in `VectorStore` for scanning the KB
- Cache-bust marker file written after ingest/reclassify
- Dynamic `list_tools()` descriptions with top-20 filter values

### Plan 17-03: list_filter_options Tool
- New MCP tool `list_filter_options(field?, collection?)` registered in `server.py`
- Integration smoke test for tool registration

## Self-Check: PASSED
- [x] infer_module() created with MODULE_PATTERNS table
- [x] Module field in classify() output and Qdrant payload
- [x] Module filter in search_kb, list_documents
- [x] FilterTermsCache with cache-bust marker refresh
- [x] get_distinct_values() scans KB for unique attribute values
- [x] Dynamic list_tools() descriptions (top-20)
- [x] list_filter_options MCP tool registered and implemented
- [x] 33 new tests + 1 integration smoke test
