# Plan 28c-04 SUMMARY: Document Export

## Objective

Add synchronous CSV/JSON document export endpoint that respects all active filters.

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_admin_ui.py -v` | ✅ 6/6 PASS |
| `pytest tests/test_ui_routes.py -v` | ✅ 14/14 PASS |

## Key Files Created/Modified

- `kb_server/ui/routes_admin.py` — Added `GET /api/v1/documents/export?format=csv|json` with filter params (product, doc_type, vendor, file_type, status)

## Implementation Notes

- CSV export uses `csv.DictWriter` with column headers from document field names
- JSON export returns formatted JSON with `indent=2`
- Both formats include `Content-Disposition: attachment` header for browser download
- Max 30,000 documents per export (no pagination — single synchronous response)
- All active filter params passed through to `get_documents()`
