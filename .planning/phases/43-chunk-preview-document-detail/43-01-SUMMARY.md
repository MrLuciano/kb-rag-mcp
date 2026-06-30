# Plan 43-01 SUMMARY: Chunk Preview in Document Detail

## Objective

Inline chunk viewer on the existing `/ui/document/{id}` page showing all chunks for a document with Bootstrap accordion, search term highlighting, and HTMX progressive reveal.

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_ui_routes.py -v` | ✅ 20/20 PASS |
| `pytest tests/test_admin_ui.py -v` | ✅ 15/15 PASS |
| `pytest tests/test_health.py -v` | ✅ 5/5 PASS |

## Key Files Created/Modified

- `kb_server/ui/app.py` — Added `highlight_term(text, query)` Jinja2 global for XSS-safe `<mark>` wrapping
- `kb_server/ui/routes.py` — Extended `document_detail` with `?q=` param, lazy VectorStore scroll for chunks, chunk list in template context; added `/ui/document/{id}/chunks` HTMX partial endpoint
- `kb_server/ui/templates/document.html` — Added Bootstrap accordion below metadata: first 10 chunks expanded, remaining collapsed, "Show next 10" HTMX button, search term highlighting, empty state
- `kb_server/ui/templates/document_chunks.html` — HTMX partial for progressive chunk loading with show-more/show-less toggle
- `tests/test_ui_routes.py` — Added TestChunkPreview class (6 tests: q param, highlight_term registration and behavior, template existence)

## Implementation Notes

- VectorStore queried lazily via scroll with `source_file` filter — graceful degradation on Qdrant errors
- `highlight_term` uses iterative regex matching with HTML escaping for XSS safety
- Chunks sorted by `chunk_index` for consistent display order
- First 10 chunks expanded by default (D-05), remaining collapsed, HTMX "Show next 10" for progressive reveal
- Empty state shows "Chunks Unavailable" when Qdrant is unreachable (non-breaking)
