---
phase: 28c-admin-spa-panel
plan: 03
type: execute
wave: 3
depends_on:
  - 28c-admin-spa-panel
files_modified:
  - kb_server/ui/routes_admin.py
  - kb_server/ui/templates/admin/tab_documents.html
  - tests/test_admin_ui.py
autonomous: true
requirements:
  - FILT-01
  - FILT-02
  - FILT-03
  - FILT-04
  - FILT-05
must_haves:
  truths:
    - Documents tab shows date range filter (created_at from/to), file type multi-select, vendor and product dropdowns
    - Vendor and product dropdowns are populated from distinct values in the database
    - Filter state is reflected in URL query parameters (shareable/bookmarkable)
    - "Clear All Filters" button resets all active filters
    - File type filter allows multi-select: PDF, DOCX, XLSX, PPTX, MD, TXT
  artifacts:
    - path: "kb_server/ui/templates/admin/tab_documents.html"
      provides: "Advanced filter UI with date range, file type multi-select, vendor/product dropdowns"
      contains: "date-from, date-to, file-type, vendor-select, product-select, clear-filters"
      min_lines: 100
    - path: "kb_server/ui/routes_admin.py"
      provides: "Enhanced browse endpoint with date range and file type filter params"
      contains: "date_from, date_to, file_type"
      min_lines: 30
    - path: "tests/test_admin_ui.py"
      provides: "Advanced filter tests"
      contains: "test_filters_"
      min_lines: 50
  key_links:
    - from: "kb_server/ui/templates/admin/tab_documents.html"
      to: "kb_server/ui/routes.py"
      via: "GET /ui/browse with filter query params"
      pattern: "date_from|date_to|file_type"
    - from: "kb_server/ui/templates/admin/tab_documents.html"
      to: "window.location"
      via: "URL query parameter sync"
      pattern: "URLSearchParams"
---

<objective>
Add advanced filter capabilities to the Documents tab: date range filter (created_at from/to), file type multi-select (PDF, DOCX, XLSX, PPTX, MD, TXT), vendor and product dropdowns populated from distinct values, filter state reflected in URL query parameters for shareable/bookmarkable URLs, and a "Clear All Filters" button.

**Purpose:** The basic browse view at /ui/browse has filters but without date range, file type multi-select, or value-populated dropdowns. Advanced filters enable users to precisely narrow down document lists by ingestion date, file format, and classification metadata. URL query parameter persistence allows sharing filtered views with team members or bookmarking specific searches.

**Output:** Enhanced tab_documents.html with advanced filter bar, updated routes.py/routes_admin.py with new filter params, distinct-value endpoints for vendor/product dropdowns, and test coverage.

**Artifacts this plan produces:**

| Symbol | Kind | Location |
|--------|------|----------|
| `GET /api/v1/documents/filter-values` | API endpoint | `kb_server/ui/routes_admin.py` |
| `Advanced Filter Bar` | HTML component | `kb_server/ui/templates/admin/tab_documents.html` |
| `resetFilters()` | Alpine.js method | `kb_server/ui/templates/admin/tab_documents.html` |
| `syncFiltersToUrl()` | Alpine.js method | `kb_server/ui/templates/admin/tab_documents.html` |
</objective>

<execution_context>
@/home/admin/.config/opencode/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@kb_server/ui/routes_admin.py
@kb_server/ui/templates/admin/tab_documents.html
@kb_server/ui/routes.py
@kb_server/ui/templates/browse.html
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Add distinct-values API endpoint for vendor/product filter dropdowns (per FILT-03)</name>
  <files>kb_server/ui/routes_admin.py, tests/test_admin_ui.py</files>
  <read_first>kb_server/ui/routes.py</read_first>
  <action>
    Step 1 — Read the existing browse.html and routes.py to understand the current filter model. The browse page uses direct SQL queries on the `files` table with simple WHERE clauses.

    Step 2 — Write failing tests in TestAdvancedFilters class:
    `test_filter_values_vendor` — GET /api/v1/documents/filter-values returns 200 with JSON containing "vendors" array
    `test_filter_values_product` — response contains "products" array
    These use TestClient on the UI app (same as other admin tests).

    Step 3 — Add filter-values endpoint to `kb_server/ui/routes_admin.py`:

    ```python
    @app.get("/api/v1/documents/filter-values")
    async def get_document_filter_values():
        """Return distinct filter values (vendors, products, file types)."""
        import sqlite3
        from pathlib import Path
        db_path = Path("data/kb_metadata.db")

        if not db_path.exists():
            return {"vendors": [], "products": [], "file_types": []}

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        def _distinct(column: str) -> list[str]:
            rows = cursor.execute(
                f"SELECT DISTINCT {column} FROM files "
                f"WHERE {column} IS NOT NULL AND {column} != '' "
                f"ORDER BY {column}"
            ).fetchall()
            return [r[0] for r in rows]

        result = {
            "vendors": _distinct("vendor"),
            "products": _distinct("product"),
            "file_types": _distinct("doc_type"),
        }
        conn.close()
        return result
    ```

    Step 4 — Run tests to verify they pass.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py::TestAdvancedFilterValues -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - GET /api/v1/documents/filter-values returns JSON with "vendors", "products", "file_types" arrays
    - Each array contains distinct, non-null, non-empty values from the files table
    - Returns empty arrays when DB doesn't exist yet
  </acceptance_criteria>
  <done>Filter-values API endpoint created and tested.</done>
</task>

<task type="auto" tdd="true">
  <name>Update get_documents() in routes.py with date range and file type filter params (per FILT-01, FILT-02)</name>
  <files>kb_server/ui/routes.py, tests/test_admin_ui.py</files>
  <read_first>kb_server/ui/routes.py</read_first>
  <action>
    Step 1 — Write failing tests for enhanced filters:
    `test_get_documents_date_range` — verifies date_from/date_to are passed as SQL params
    `test_get_documents_file_type` — verifies file_type filter works

    Step 2 — Update `get_documents()` in `kb_server/ui/routes.py` to accept date range and file_type params:

    Update the function signature:
    ```python
    def get_documents(
        product: Optional[str] = None,
        doc_type: Optional[str] = None,
        version: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,   # ISO date string
        date_to: Optional[str] = None,     # ISO date string
        file_type: Optional[str] = None,   # comma-separated: "PDF,DOCX"
        vendor: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
    ```

    Add filter logic to the WHERE clause builder:

    ```python
    if date_from:
        where_clauses.append("indexed_at >= ?")
        params.append(date_from)
    if date_to:
        where_clauses.append("indexed_at <= ?")
        params.append(date_to + " 23:59:59")
    if file_type:
        # file_type is comma-separated: "PDF,DOCX" → WHERE doc_type IN ('PDF','DOCX')
        types = [t.strip().lower() for t in file_type.split(",") if t.strip()]
        if types:
            placeholders = ",".join("?" for _ in types)
            where_clauses.append(f"LOWER(doc_type) IN ({placeholders})")
            params.extend(types)
    if vendor:
        where_clauses.append("vendor = ?")
        params.append(vendor)
    ```

    Also update `browse_documents` endpoint to accept and forward new params:

    ```python
    @app.get("/ui/browse", response_class=HTMLResponse)
    async def browse_documents(
        request: Request,
        product: Optional[str] = Query(None),
        doc_type: Optional[str] = Query(None),
        version: Optional[str] = Query(None),
        status: Optional[str] = Query(None),
        date_from: Optional[str] = Query(None),
        date_to: Optional[str] = Query(None),
        file_type: Optional[str] = Query(None),
        vendor: Optional[str] = Query(None),
        page: int = Query(1, ge=1)
    ):
        limit = 25  # per D-09: 25 results per page
        offset = (page - 1) * limit
        documents, total = get_documents(
            product=product, doc_type=doc_type, version=version,
            status=status, date_from=date_from, date_to=date_to,
            file_type=file_type, vendor=vendor,
            limit=limit, offset=offset,
        )
        # ... rest stays the same but passes filters in context ...
    ```

    Update the filters dict in the TemplateResponse context to include new filters.

    Step 3 — Run tests to verify they pass.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py::TestAdvancedFilterValues -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - get_documents() accepts date_from, date_to, file_type, vendor params
    - date_from adds "indexed_at >= ?" to WHERE clause
    - date_to adds "indexed_at <= ?" to WHERE clause
    - file_type splits comma-separated values into IN clause
    - vendor adds "vendor = ?" to WHERE clause
    - browse_documents endpoint forwards new params to get_documents()
  </acceptance_criteria>
  <done>get_documents() enhanced with date range, file type, and vendor filter support.</done>
</task>

<task type="auto">
  <name>Create advanced filter UI in tab_documents.html with URL query param sync (per FILT-04, FILT-05)</name>
  <files>kb_server/ui/templates/admin/tab_documents.html, tests/test_admin_ui.py</files>
  <read_first>kb_server/ui/templates/admin/tab_documents.html</read_first>
  <action>
    Step 1 — Replace the content of `kb_server/ui/templates/admin/tab_documents.html` with an advanced filter bar that includes:

    ```html
    <div x-data="documentsFilter()" x-init="initFilters()">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h3 class="mb-0">Documents</h3>
            <button class="btn btn-outline-success btn-sm"
                    id="export-btn"
                    x-on:click="exportDocuments()"
                    title="Export filtered results">
                📥 Export
            </button>
        </div>
        <p class="text-muted">Browse and manage indexed documents. Use filters below to narrow results.</p>

        <!-- Advanced Filter Bar -->
        <div class="card mb-3">
            <div class="card-body">
                <div class="row g-2">
                    <!-- Date Range -->
                    <div class="col-md-3">
                        <label class="form-label small">From Date</label>
                        <input type="date" class="form-control form-control-sm"
                               x-model="filters.date_from"
                               x-on:change="applyFilters()">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small">To Date</label>
                        <input type="date" class="form-control form-control-sm"
                               x-model="filters.date_to"
                               x-on:change="applyFilters()">
                    </div>

                    <!-- File Type Multi-Select -->
                    <div class="col-md-3">
                        <label class="form-label small">File Type</label>
                        <div x-data="{ open: false }" class="dropdown">
                            <button class="btn btn-sm btn-outline-secondary w-100 text-start dropdown-toggle"
                                    @click="open = !open">
                                <span x-text="selectedFileTypes() || 'All types'"></span>
                            </button>
                            <div x-show="open" @click.outside="open = false"
                                 class="dropdown-menu show p-2" style="max-height: 200px; overflow-y: auto;">
                                <template x-for="ft in ['PDF','DOCX','XLSX','PPTX','MD','TXT']" :key="ft">
                                    <label class="dropdown-item d-flex align-items-center gap-2">
                                        <input type="checkbox" :value="ft" x-model="filters.file_types"
                                               @change="open = true; applyFilters()">
                                        <span x-text="ft"></span>
                                    </label>
                                </template>
                            </div>
                        </div>
                    </div>

                    <!-- Vendor Dropdown -->
                    <div class="col-md-3">
                        <label class="form-label small">Vendor</label>
                        <select class="form-select form-select-sm"
                                x-model="filters.vendor"
                                x-on:change="applyFilters()">
                            <option value="">All Vendors</option>
                            <template x-for="v in filterOptions.vendors" :key="v">
                                <option :value="v" x-text="v"></option>
                            </template>
                        </select>
                    </div>

                    <!-- Product Dropdown -->
                    <div class="col-md-3">
                        <label class="form-label small">Product</label>
                        <select class="form-select form-select-sm"
                                x-model="filters.product"
                                x-on:change="applyFilters()">
                            <option value="">All Products</option>
                            <template x-for="p in filterOptions.products" :key="p">
                                <option :value="p" x-text="p"></option>
                            </template>
                        </select>
                    </div>

                    <!-- Actions -->
                    <div class="col-md-3 d-flex align-items-end">
                        <button class="btn btn-outline-secondary btn-sm w-100"
                                x-on:click="clearFilters()">Clear All Filters</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Document Browse Content -->
        <div id="browse-content"
             hx-get="/ui/browse"
             hx-trigger="load"
             hx-target="this"
             hx-swap="innerHTML">
            <p class="text-muted">Loading documents...</p>
        </div>
    </div>

    <script>
    function documentsFilter() {
        return {
            filters: {
                date_from: '',
                date_to: '',
                file_types: [],
                vendor: '',
                product: '',
            },
            filterOptions: {
                vendors: [],
                products: [],
                file_types: ['PDF', 'DOCX', 'XLSX', 'PPTX', 'MD', 'TXT'],
            },

            initFilters() {
                // Restore filters from URL query params
                const params = new URLSearchParams(window.location.search);
                if (params.has('date_from')) this.filters.date_from = params.get('date_from');
                if (params.has('date_to')) this.filters.date_to = params.get('date_to');
                if (params.has('file_type')) this.filters.file_types = params.get('file_type').split(',');
                if (params.has('vendor')) this.filters.vendor = params.get('vendor');
                if (params.has('product')) this.filters.product = params.get('product');

                // Load vendor/product dropdown values
                fetch('/api/v1/documents/filter-values')
                    .then(r => r.json())
                    .then(data => {
                        this.filterOptions.vendors = data.vendors || [];
                        this.filterOptions.products = data.products || [];
                    })
                    .catch(() => {});
            },

            selectedFileTypes() {
                if (this.filters.file_types.length === 0) return '';
                if (this.filters.file_types.length <= 3) return this.filters.file_types.join(', ');
                return this.filters.file_types.length + ' types';
            },

            applyFilters() {
                this.syncFiltersToUrl();
                const browse = document.getElementById('browse-content');
                if (browse) {
                    let url = '/ui/browse';
                    const params = [];
                    if (this.filters.date_from) params.push('date_from=' + encodeURIComponent(this.filters.date_from));
                    if (this.filters.date_to) params.push('date_to=' + encodeURIComponent(this.filters.date_to));
                    if (this.filters.file_types.length > 0) params.push('file_type=' + this.filters.file_types.join(','));
                    if (this.filters.vendor) params.push('vendor=' + encodeURIComponent(this.filters.vendor));
                    if (this.filters.product) params.push('product=' + encodeURIComponent(this.filters.product));
                    if (params.length > 0) url += '?' + params.join('&');
                    htmx.ajax('GET', url, { target: '#browse-content', swap: 'innerHTML' });
                }
            },

            clearFilters() {
                this.filters.date_from = '';
                this.filters.date_to = '';
                this.filters.file_types = [];
                this.filters.vendor = '';
                this.filters.product = '';
                this.syncFiltersToUrl();
                const browse = document.getElementById('browse-content');
                if (browse) {
                    htmx.ajax('GET', '/ui/browse', { target: '#browse-content', swap: 'innerHTML' });
                }
            },

            syncFiltersToUrl() {
                const params = new URLSearchParams();
                if (this.filters.date_from) params.set('date_from', this.filters.date_from);
                if (this.filters.date_to) params.set('date_to', this.filters.date_to);
                if (this.filters.file_types.length > 0) params.set('file_type', this.filters.file_types.join(','));
                if (this.filters.vendor) params.set('vendor', this.filters.vendor);
                if (this.filters.product) params.set('product', this.filters.product);
                const qs = params.toString();
                const newUrl = window.location.pathname + (qs ? '?' + qs : '');
                window.history.replaceState({}, '', newUrl);
            },

            exportDocuments() {
                const params = new URLSearchParams();
                params.set('format', 'json');
                if (this.filters.date_from) params.set('date_from', this.filters.date_from);
                if (this.filters.date_to) params.set('date_to', this.filters.date_to);
                if (this.filters.file_types.length > 0) params.set('file_type', this.filters.file_types.join(','));
                if (this.filters.vendor) params.set('vendor', this.filters.vendor);
                if (this.filters.product) params.set('product', this.filters.product);
                window.open('/api/v1/documents/export?' + params.toString(), '_blank');
            }
        };
    }
    </script>
    ```

    Step 2 — Update browse_documents endpoint in routes.py to handle date_from, date_to, file_type, vendor query params (already done in Task 2). Also update the TemplateResponse filters context dict.

    Step 3 — Run tests.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - Filter bar shows date range inputs (from/to), file type multi-select dropdown, vendor/product dropdowns
    - File type multi-select includes: PDF, DOCX, XLSX, PPTX, MD, TXT
    - Vendor/product dropdowns populated from /api/v1/documents/filter-values
    - Selecting a filter triggers HTMX re-load with filter params
    - Filter state reflected in URL query params (date_from, date_to, file_type, vendor, product)
    - "Clear All Filters" resets all filters, clears URL params, reloads document list
    - Export button opens /api/v1/documents/export with current filter params
  </acceptance_criteria>
  <done>Advanced filter UI with date range, file type multi-select, vendor/product dropdowns, URL sync, and clear all created and tested.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Browser → /ui/browse?filter_params | Untrusted filter params reach SQL query builder |
| Browser → /api/v1/documents/filter-values | Distinct value enumeration |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-28c-10 | Tampering | SQL injection via filter params | mitigate | Parameterized SQL queries (?, ?) used throughout get_documents(); no string concatenation of user input |
| T-28c-11 | Information Disclosure | Filter-values reveals distinct vendor/product names | accept | Internal admin UI; metadata already visible in browse table |
</threat_model>

<verification>
### Per-Task Verification
```bash
cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -20
```

### Manual Verification
1. Navigate to Documents tab — verify filter bar with 5 filter controls
2. Select date range — verify browse content reloads with filtered results
3. Check file type multi-select — verify comma-separated IN clause
4. Check vendor/product dropdowns — verify populated from distinct values
5. Verify URL bar updates with query params after filter change
6. Click "Clear All Filters" — verify all filters reset, params cleared
7. Copy URL with filters, open new tab — verify filters restore correctly
</verification>

<success_criteria>
- Date range filter (created_at from/to) correctly filters documents
- File type multi-select (PDF, DOCX, XLSX, PPTX, MD, TXT) generates proper SQL IN clause
- Vendor and product dropdowns show distinct values from database
- URL query parameters (date_from, date_to, file_type, vendor, product) reflect active filters
- "Clear All Filters" resets all filters, clears URL params, reloads full list
- All tests pass; no SQL injection vectors (parameterized queries verified)
</success_criteria>

<output>
  <file path="kb_server/ui/routes_admin.py" summary="Added /api/v1/documents/filter-values endpoint" />
  <file path="kb_server/ui/routes.py" summary="Enhanced get_documents() with date_from, date_to, file_type, vendor params" />
  <file path="kb_server/ui/templates/admin/tab_documents.html" summary="Advanced filter bar with Alpine.js state management, URL sync, clear all" />
  <file path="tests/test_admin_ui.py" summary="Advanced filter tests (filter values API, SQL params)" />
</output>
