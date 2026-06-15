---
phase: 28c-admin-spa-panel
plan: 04
type: execute
wave: 3
depends_on:
  - 28c-admin-spa-panel
files_modified:
  - kb_server/ui/routes_admin.py
  - tests/test_admin_ui.py
autonomous: true
requirements:
  - EXPT-01
  - EXPT-02
  - EXPT-03
  - EXPT-04
must_haves:
  truths:
    - User can click Export button and download filtered documents as CSV or JSON
    - Export respects all active filters (date range, file type, vendor, product)
    - CSV export includes headers and comma-separated values
    - JSON export returns array of document objects
    - Large exports show a progress indicator while generating
  artifacts:
    - path: "kb_server/ui/routes_admin.py"
      provides: "Document export endpoint supporting CSV and JSON"
      contains: "export_documents, csv.writer, json.dumps"
      min_lines: 60
    - path: "tests/test_admin_ui.py"
      provides: "Export endpoint tests"
      contains: "test_export_csv, test_export_json, test_export_with_filters"
      min_lines: 40
  key_links:
    - from: "kb_server/ui/routes_admin.py"
      to: "kb_server/ui/routes.py"
      via: "get_documents() for data sourcing"
      pattern: "get_documents"
    - from: "kb_server/ui/templates/admin/tab_documents.html"
      to: "kb_server/ui/routes_admin.py"
      via: "GET /api/v1/documents/export?format=..."
      pattern: "export"
---

<objective>
Add document export functionality to the Documents tab: export button triggers filtered CSV or JSON download via `/api/v1/documents/export`, respects all active filters (date range, file type, vendor, product), shows progress indicator for large datasets.

**Purpose:** Users need to download filtered document lists for offline analysis, reporting, or audit purposes. CSV format enables spreadsheet import; JSON enables programmatic consumption. The export respects all active filters so users export exactly the subset they're working with.

**Design decisions (per D-12):** Synchronous CSV/JSON download — export endpoint returns the file directly. HTMX-triggered download via anchor click. Background jobs reserved for future scaling — current deployment handles synchronous export for datasets up to ~10,000 rows.

**Output:** `/api/v1/documents/export` endpoint (format=csv|json, filter params), progress indicator in tab_documents.html, and test coverage.

**Artifacts this plan produces:**

| Symbol | Kind | Location |
|--------|------|----------|
| `GET /api/v1/documents/export` | API endpoint | `kb_server/ui/routes_admin.py` |
| CSV export generator | Logic | `kb_server/ui/routes_admin.py` |
| JSON export generator | Logic | `kb_server/ui/routes_admin.py` |
</objective>

<execution_context>
@/home/admin/.config/opencode/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@kb_server/ui/routes_admin.py
@kb_server/ui/routes.py
@kb_server/ui/templates/admin/tab_documents.html
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Create document export endpoint with CSV and JSON support (per EXPT-01, EXPT-02, EXPT-03)</name>
  <files>kb_server/ui/routes_admin.py, tests/test_admin_ui.py</files>
  <read_first>kb_server/ui/routes.py, kb_server/ui/routes_admin.py</read_first>
  <action>
    Step 1 — Read the existing get_documents() function in routes.py to understand the data format. It returns a list of dicts with keys like id, source_file, product, doc_type, version, status, chunks_stored.

    Step 2 — Write failing tests in TestDocumentExport class:
    `test_export_csv_returns_200` — GET /api/v1/documents/export?format=csv returns 200 with text/csv content type
    `test_export_json_returns_200` — GET /api/v1/documents/export?format=json returns 200 with application/json
    `test_export_csv_has_headers` — CSV response contains header row with column names
    `test_export_with_filters` — export with filter params returns filtered data
    `test_export_invalid_format_returns_400` — GET with format=xml returns 400

    Step 3 — Add export endpoint to `kb_server/ui/routes_admin.py`:

    ```python
    import csv
    import io
    import json
    from typing import Optional
    from fastapi import Query
    from fastapi.responses import Response
    from kb_server.ui.routes import get_documents


    @app.get("/api/v1/documents/export")
    async def export_documents(
        format: str = Query("csv", regex="^(csv|json)$"),
        date_from: Optional[str] = Query(None),
        date_to: Optional[str] = Query(None),
        file_type: Optional[str] = Query(None),
        vendor: Optional[str] = Query(None),
        product: Optional[str] = Query(None),
        doc_type: Optional[str] = Query(None),
        status: Optional[str] = Query(None),
        limit: int = Query(10000, ge=1, le=50000),
    ):
        """Export filtered documents as CSV or JSON.

        Respects all active filter params. Default format is CSV.
        Maximum export size is 50,000 rows (configurable via limit param).
        """
        documents, total = get_documents(
            product=product,
            doc_type=doc_type or file_type,
            status=status,
            date_from=date_from,
            date_to=date_to,
            file_type=file_type,
            vendor=vendor,
            limit=limit,
            offset=0,
        )

        if not documents:
            if format == "csv":
                return Response(content="No documents match filter criteria.\n",
                                media_type="text/plain", status_code=200)
            return Response(content=json.dumps([]), media_type="application/json",
                            status_code=200)

        if format == "csv":
            output = io.StringIO()
            # Determine fieldnames from first document (stable order)
            fieldnames = [
                "id", "source_file", "product", "doc_type",
                "version", "status", "chunks_stored",
            ]
            # Add any extra keys found in documents
            for doc in documents:
                for key in doc:
                    if key not in fieldnames:
                        fieldnames.append(key)

            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for doc in documents:
                writer.writerow(doc)

            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=documents.csv",
                    "X-Total-Count": str(total),
                },
            )

        # JSON format
        # Convert to serializable format (handle dates, etc.)
        clean_docs = []
        for doc in documents:
            clean = {}
            for k, v in doc.items():
                if hasattr(v, "isoformat"):
                    clean[k] = v.isoformat()
                else:
                    clean[k] = v
            clean_docs.append(clean)

        return Response(
            content=json.dumps(clean_docs, indent=2, default=str),
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=documents.json",
                "X-Total-Count": str(total),
            },
        )
    ```

    Step 4 — Also add a validation check for the format param (FastAPI regex handles this, but add explicit 400 for safety):

    Actually, FastAPI's `regex` on Query handles validation automatically — an invalid format like "xml" will return a 422 validation error from FastAPI.

    Step 5 — Run tests to verify they pass.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py::TestDocumentExport -x -v 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - GET /api/v1/documents/export?format=csv returns 200 with text/csv content type
    - CSV response includes Content-Disposition: attachment header
    - CSV response has header row with column names followed by data rows
    - GET /api/v1/documents/export?format=json returns 200 with application/json
    - JSON response is a valid JSON array of document objects
    - Export with filter params (date_from, file_type, etc.) returns filtered subset
    - Invalid format (e.g., format=xml) returns 422 validation error
    - X-Total-Count header present in response
    - Maximum export limit is 50,000 rows
  </acceptance_criteria>
  <done>Document export endpoint with CSV and JSON support created and tested.</done>
</task>

<task type="auto">
  <name>Wire export button in tab_documents.html with progress indicator for large exports (per EXPT-01, EXPT-04)</name>
  <files>kb_server/ui/templates/admin/tab_documents.html, tests/test_admin_ui.py</files>
  <read_first>kb_server/ui/templates/admin/tab_documents.html</read_first>
  <action>
    Step 1 — The Documents tab template already has the export button wired (from 28c-03) via the `exportDocuments()` Alpine.js method. Update it to:

    1. Show a format chooser (CSV/JSON dropdown) before triggering export
    2. Show a progress/loading indicator for large exports
    3. Add HTMX-triggered inline export for browser-based download

    Update the export button section in `tab_documents.html` — replace the existing export button with a format dropdown + button:

    ```html
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h3 class="mb-0">Documents</h3>
        <div class="d-flex align-items-center gap-2">
            <!-- Export format selector -->
            <select class="form-select form-select-sm" style="width: auto;"
                    x-model="exportFormat"
                    aria-label="Export format">
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
            </select>
            <button class="btn btn-outline-success btn-sm"
                    x-on:click="exportDocuments()"
                    :disabled="exporting"
                    x-text="exporting ? 'Exporting...' : '📥 Export'">
            </button>
        </div>
    </div>
    ```

    Add `exportFormat: 'csv'` and `exporting: false` to the Alpine.js data object in `documentsFilter()`.
    Update the `exportDocuments()` method to include format and progress:

    ```javascript
    exportDocuments() {
        this.exporting = true;
        const params = new URLSearchParams();
        params.set('format', this.exportFormat);
        if (this.filters.date_from) params.set('date_from', this.filters.date_from);
        if (this.filters.date_to) params.set('date_to', this.filters.date_to);
        if (this.filters.file_types.length > 0) params.set('file_type', this.filters.file_types.join(','));
        if (this.filters.vendor) params.set('vendor', this.filters.vendor);
        if (this.filters.product) params.set('product', this.filters.product);

        const url = '/api/v1/documents/export?' + params.toString();

        // For large exports, fetch first to get total count, then stream download
        fetch(url, { method: 'HEAD' })
            .then(r => {
                const total = parseInt(r.headers.get('X-Total-Count') || '0', 10);
                if (total > 5000) {
                    // Show progress indicator for large exports
                    this.showProgress = true;
                    this.progressTotal = total;
                }
                // Trigger download
                window.open(url, '_blank');
                setTimeout(() => {
                    this.exporting = false;
                    this.showProgress = false;
                }, 2000);
            })
            .catch(() => {
                window.open(url, '_blank');
                this.exporting = false;
            });
    },
    ```

    Add progress indicator to the template (after the filter bar):

    ```html
    <!-- Export progress indicator -->
    <div x-show="showProgress" style="display: none;" class="alert alert-info mb-3 d-flex align-items-center gap-2">
        <div class="spinner-border spinner-border-sm text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <span x-text="'Exporting ' + progressTotal + ' documents...'"></span>
    </div>
    ```

    Add to the Alpine.js data initialization:
    ```javascript
    exportFormat: 'csv',
    exporting: false,
    showProgress: false,
    progressTotal: 0,
    ```

    Step 2 — Write a test `test_export_button_in_tab` that verifies the tab_documents.html contains export-related elements:
    - Contains "Export" text
    - Contains "csv" option
    - Contains "json" option
    - Contains "exportDocuments" function reference

    This test reads the template file directly (not via HTTP) to verify presence of expected elements.

    Step 3 — Run all tests.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - Documents tab shows Export button with CSV/JSON format selector
    - CSV export button opens /api/v1/documents/export?format=csv with current filter params
    - JSON export opens /api/v1/documents/export?format=json with current filter params
    - Progress indicator (spinner + message) shows for exports with >5000 documents
    - Button shows "Exporting..." and is disabled during export
    - All filter params (date_from, date_to, file_type, vendor, product) are forwarded to export URL
  </acceptance_criteria>
  <done>Export button with format selector and progress indicator wired in Documents tab; tests passing.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Browser → /api/v1/documents/export | Filter params from URL query reach data query builder |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-28c-12 | Tampering | Large export DoS (no explicit limit) | mitigate | Export capped at 50,000 rows via `limit` Query param; FastAPI validates (ge=1, le=50000) |
| T-28c-13 | Information Disclosure | Export exposes all document metadata | accept | Admin-only feature; data is already visible in browse UI |
| T-28c-14 | Denial of Service | Synchronous large export blocks server | accept | Current synchronous approach sufficient for expected dataset sizes; background job deferred per D-12 |
</threat_model>

<verification>
### Per-Task Verification
```bash
cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py::TestDocumentExport -x -v 2>&1 | tail -15
```

### Manual Verification
1. Navigate to Documents tab — verify Export button with CSV/JSON format dropdown
2. Select CSV, click Export — verify CSV file downloads with headers + data
3. Select JSON, click Export — verify JSON file downloads with document array
4. Apply filters (e.g., date range), export — verify only filtered documents in export
5. Verify X-Total-Count header matches filtered result count

### Regression Check
```bash
cd /home/admin/kb-rag-mcp && python -m pytest -x --timeout=60 2>&1 | tail -10
```
Expected: No regressions.
</verification>

<success_criteria>
- Export button in Documents tab downloads filtered results as CSV or JSON
- CSV export has header row + data rows with Content-Disposition: attachment
- JSON export returns valid JSON array with Content-Disposition: attachment
- Export respects all active filters (date range, file type, vendor, product)
- Export capped at 50,000 rows
- Progress indicator shown for large exports
- X-Total-Count header indicates total matching rows
- All tests pass; no regressions
</success_criteria>

<output>
  <file path="kb_server/ui/routes_admin.py" summary="Added /api/v1/documents/export endpoint with CSV/JSON support" />
  <file path="kb_server/ui/templates/admin/tab_documents.html" summary="Added export format selector, progress indicator, and wired exportDocuments()" />
  <file path="tests/test_admin_ui.py" summary="Document export tests (CSV, JSON, filter params, invalid format)" />
</output>
