---
phase: 28c-admin-spa-panel
plan: 02
type: execute
wave: 3
depends_on:
  - 28c-admin-spa-panel
  - 28b-auth-api
  - 39-observability
  - 40-config-backlog
files_modified:
  - kb_server/ui/routes_admin.py
  - kb_server/ui/templates/admin/tab_monitoring.html
  - kb_server/ui/templates/admin/tab_admin.html
  - kb_server/ui/templates/admin/tab_profile.html
  - kb_server/ui/templates/admin/_monitor_lights.html
  - kb_server/ui/templates/admin/_config_table.html
  - kb_server/ui/templates/admin/_profile_content.html
  - kb_server/ui/templates/browse.html
  - tests/test_admin_ui.py
autonomous: true
requirements:
  - SPA-06
  - SPA-07
  - SPA-08
  - SPA-09
must_haves:
  truths:
    - Monitor lights bar shows 7 component health indicators with color-coded badges, auto-refreshing every 30s
    - Admin Config tab shows config values grouped by category with inline editing via Alpine.js
    - Profile tab shows user info, API key management (create/list/revoke), GDPR export and erasure buttons
    - Document browse has checkbox selection with cleanup toolbar (Delete, Re-ingest, Delete Failed)
    - Per-document Actions dropdown includes View, Delete, Re-ingest
  artifacts:
    - path: "kb_server/ui/templates/admin/_monitor_lights.html"
      provides: "Health card display for 7 components"
      contains: "check_all_components, bg-success/bg-danger/bg-secondary"
      min_lines: 50
    - path: "kb_server/ui/templates/admin/_config_table.html"
      provides: "Config table with Alpine.js inline editing"
      contains: "x-data, editing, dblclick, hx-put"
      min_lines: 80
    - path: "kb_server/ui/templates/admin/_profile_content.html"
      provides: "Profile tab content with API key CRUD and GDPR"
      contains: "profilePage, initProfile, generateKey, revokeKey"
      min_lines: 120
    - path: "kb_server/ui/routes_admin.py"
      provides: "Tab content endpoints (monitor-lights, config-table, profile-content) and document cleanup API"
      contains: "admin_tab_monitor_lights, delete_document, reingest_document"
      min_lines: 120
  key_links:
    - from: "kb_server/ui/templates/admin/_monitor_lights.html"
      to: "kb_server/health.py"
      via: "check_all_components()"
      pattern: "check_all_components"
    - from: "kb_server/ui/templates/admin/_config_table.html"
      to: "kb_server/config/router.py"
      via: "PUT /api/v1/config/{key}"
      pattern: "/api/v1/config"
    - from: "kb_server/ui/templates/browse.html"
      to: "kb_server/ui/routes_admin.py"
      via: "DELETE /api/v1/documents/{source_file}"
      pattern: "api/v1/documents"
---

<objective>
Implement the four tab content panels that provide actual admin functionality: Monitor Lights bar (7 health components with auto-refresh), Admin Config page (inline editing with Alpine.js), Profile tab (API key management, GDPR export/erasure), and Document browse cleanup (checkbox selection, delete/re-ingest per document).

**Purpose:** These four tab panels transform the SPA shell from a static UI into a functional admin panel. The monitor lights give ops teams real-time system health visibility. The config page enables runtime configuration changes without file editing. The profile tab puts API key management and GDPR compliance tools in users' hands. The browse cleanup adds document lifecycle management to the existing browse view.

**Output:** `_monitor_lights.html` with 7 health cards, `_config_table.html` with Alpine.js inline editing, `_profile_content.html` with Alpine.js key management, enhanced `browse.html` with checkbox selection and cleanup toolbar, extended `routes_admin.py` with tab content endpoints and document cleanup API, and test coverage.

**Artifacts this plan produces:**

| Symbol | Kind | Location |
|--------|------|----------|
| `GET /admin/tabs/monitor-lights` | Route | `kb_server/ui/routes_admin.py` |
| `GET /admin/tabs/config-table` | Route | `kb_server/ui/routes_admin.py` |
| `GET /admin/tabs/profile-content` | Route | `kb_server/ui/routes_admin.py` |
| `DELETE /api/v1/documents/{source_file}` | Route | `kb_server/ui/routes_admin.py` |
| `POST /api/v1/documents/{source_file}/re-ingest` | Route | `kb_server/ui/routes_admin.py` |
| `POST /api/v1/documents/delete-failed` | Route | `kb_server/ui/routes_admin.py` |
| `profilePage()` | Alpine.js component | `kb_server/ui/templates/admin/_profile_content.html` |
| `selectAll()` | JS function | `kb_server/ui/templates/browse.html` |
| `updateToolbar()` | JS function | `kb_server/ui/templates/browse.html` |
</objective>

<execution_context>
@/home/admin/.config/opencode/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@kb_server/ui/routes_admin.py
@kb_server/ui/templates/admin/shell.html
@kb_server/ui/templates/admin/tab_monitoring.html
@kb_server/ui/templates/admin/tab_admin.html
@kb_server/ui/templates/admin/tab_profile.html
@kb_server/ui/templates/browse.html
@kb_server/health.py
@kb_server/config/loader.py
@kb_server/auth/router.py
@tests/test_ui_routes.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Monitor Lights bar — 7 health component cards with 30s auto-refresh (per D-06, D-07, SPA-06)</name>
  <files>kb_server/ui/routes_admin.py, kb_server/ui/templates/admin/_monitor_lights.html, kb_server/ui/templates/admin/tab_monitoring.html, tests/test_admin_ui.py</files>
  <read_first>kb_server/health.py, kb_server/health_server.py</read_first>
  <action>
    Step 1 — Read the health module to understand `check_all_components()` return type. It returns a dict like:
    ```python
    {
        "vector_store": HealthStatus(healthy=True, message="Connected", latency_ms=12.3),
        "embedding": HealthStatus(healthy=True, ...),
        ...
    }
    ```

    Step 2 — Write failing tests in test_admin_ui.py TestMonitorLights class:
    `test_monitor_lights_partial_returns_200` — GET /admin/tabs/monitor-lights returns 200
    `test_monitor_lights_contains_component_names` — response contains text like "Qdrant", "Embedding", "LLM", "Cache", "Database", "Filesystem", "Grafana"

    Step 3 — Add monitor-lights endpoint to `kb_server/ui/routes_admin.py`:

    ```python
    @app.get("/admin/tabs/monitor-lights", response_class=HTMLResponse, include_in_schema=False)
    async def admin_monitor_lights(request: Request):
        """Return monitor lights bar partial with 7 component health statuses."""
        from kb_server.health import check_all_components
        from kb_server.ui.app import templates
        components = await check_all_components()
        return templates.TemplateResponse(
            request,
            "admin/_monitor_lights.html",
            {"request": request, "components": components},
        )
    ```

    Step 4 — Create `kb_server/ui/templates/admin/_monitor_lights.html`:

    ```html
    <div class="d-flex gap-3 flex-wrap mb-3">
        {% set component_labels = {
            "vector_store": "Qdrant",
            "embedding": "Embedding",
            "llm_provider": "LLM Provider",
            "cache": "Cache",
            "database": "Database",
            "filesystem": "Filesystem",
            "grafana": "Grafana",
        } %}
        {% for key, label in component_labels.items() %}
        {% set comp = components.get(key) %}
        <div class="card" style="width: 160px;" x-data="{ expanded: false }">
            <div class="card-body text-center p-2">
                <div class="mb-1">
                    {% if comp and comp.healthy == True %}
                    <span class="badge bg-success d-inline-block rounded-circle p-0"
                          style="width: 12px; height: 12px;"
                          aria-label="{{ label }} status: healthy">&nbsp;</span>
                    {% elif comp and comp.healthy == False %}
                    <span class="badge bg-danger d-inline-block rounded-circle p-0"
                          style="width: 12px; height: 12px;"
                          aria-label="{{ label }} status: unhealthy">&nbsp;</span>
                    {% elif comp and comp.healthy is none %}
                    <span class="badge bg-warning d-inline-block rounded-circle p-0"
                          style="width: 12px; height: 12px;"
                          aria-label="{{ label }} status: degraded">&nbsp;</span>
                    {% else %}
                    <span class="badge bg-secondary d-inline-block rounded-circle p-0"
                          style="width: 12px; height: 12px;"
                          aria-label="{{ label }} status: unknown">&nbsp;</span>
                    {% endif %}
                    <small class="d-block mt-1 fw-semibold">{{ label }}</small>
                </div>
                {% if comp %}
                <small class="text-muted">{{ comp.message|truncate(30) }}</small>
                {% if comp.latency_ms is not none %}
                <br><small class="text-muted">{{ "%.0f"|format(comp.latency_ms) }}ms</small>
                {% endif %}
                <br>
                <a href="#" @click.prevent="expanded = !expanded" class="small">details</a>
                <div x-show="expanded" style="display: none;" class="mt-1 text-start small">
                    <pre>{{ comp.to_dict() }}</pre>
                </div>
                {% else %}
                <small class="text-muted">Not checked</small>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
    ```

    Step 5 — Update `kb_server/ui/templates/admin/tab_monitoring.html` to load the monitor-lights partial via HTMX:

    ```html
    <h3>Monitoring</h3>
    <p class="text-muted">System health and status overview.</p>
    <div id="monitor-lights"
         hx-get="/admin/tabs/monitor-lights"
         hx-trigger="load, every 30s"
         hx-target="this"
         hx-swap="innerHTML">
        <p class="text-muted">Loading system health...</p>
    </div>
    <hr>
    <div id="grafana-embed">
        <p class="text-muted">Grafana dashboard embedding will be available after Phase 38 configuration.</p>
    </div>
    ```

    Step 6 — Run tests to verify they pass.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py::TestMonitorLights -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - GET /admin/tabs/monitor-lights returns 200 with HTML containing all 7 component labels
    - Each component card shows colored dot (green/red/yellow/gray), message, latency if available
    - "details" link toggles Alpine.js expanded view showing component data dict
    - tab_monitoring.html loads monitors on load and every 30s
  </acceptance_criteria>
  <done>Monitor Lights bar with 7 component health cards implemented and tested.</done>
</task>

<task type="auto" tdd="true">
  <name>Admin Config tab — inline editing with Alpine.js (per D-08 follow-up, SPA-08)</name>
  <files>kb_server/ui/routes_admin.py, kb_server/ui/templates/admin/tab_admin.html, kb_server/ui/templates/admin/_config_table.html, tests/test_admin_ui.py</files>
  <read_first>kb_server/config/loader.py, kb_server/ui/routes_admin.py</read_first>
  <action>
    Step 1 — Read ConfigLoader API to understand `get_all()` return format. From config SUMMARY: ConfigLoader.get_all() returns entries ordered by group/key.

    Step 2 — Write failing tests in TestAdminConfig class:
    `test_config_table_returns_200` — GET /admin/tabs/config-table returns 200
    `test_config_table_contains_config_keywords` — response contains "Group", "Key", "Value", "Type" (table headers)

    Step 3 — Add config-table endpoint to routes_admin.py:

    ```python
    @app.get("/admin/tabs/config-table", response_class=HTMLResponse, include_in_schema=False)
    async def admin_config_table(request: Request):
        """Return config table partial with all config entries."""
        from kb_server.config.loader import ConfigLoader
        from kb_server.ui.app import templates
        loader = getattr(request.app.state, "config_loader", None)
        if loader is None:
            loader = ConfigLoader()
        configs = await loader.get_all()
        return templates.TemplateResponse(
            request,
            "admin/_config_table.html",
            {"request": request, "configs": configs},
        )
    ```

    Step 4 — Create `kb_server/ui/templates/admin/tab_admin.html` (replace placeholder):

    ```html
    <h3>Admin Settings</h3>
    <p class="text-muted">System configuration. Changes apply immediately via hot-reload.</p>

    <div class="mb-3">
        <input type="text" class="form-control" id="config-search"
               placeholder="Search config keys..."
               x-on:input.debounce="filterConfig = $event.target.value.toLowerCase()"
               aria-label="Search config keys">
    </div>

    <div id="config-table"
         x-data="{ filterConfig: '' }"
         hx-get="/admin/tabs/config-table"
         hx-trigger="load"
         hx-swap="innerHTML">
        <p class="text-muted">Loading configuration...</p>
    </div>
    ```

    Step 5 — Create `kb_server/ui/templates/admin/_config_table.html`:

    ```html
    {% if configs %}
    <div class="table-responsive">
        <table class="table table-sm table-hover">
            <thead>
                <tr>
                    <th>Group</th>
                    <th>Key</th>
                    <th>Value</th>
                    <th>Type</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for cfg in configs %}
                <tr class="config-row"
                    x-data="{ editing: false, val: '{{ cfg.value|e }}' }"
                    x-show="!filterConfig || '{{ cfg.key|e }}'.toLowerCase().includes(filterConfig)
                             || '{{ cfg.group_name|e }}'.toLowerCase().includes(filterConfig)">
                    <td><span class="badge bg-secondary">{{ cfg.group_name }}</span></td>
                    <td class="config-key"><code>{{ cfg.key }}</code></td>
                    <td>
                        <template x-if="!editing">
                            <span x-text="val"
                                  @dblclick="editing = true"
                                  style="cursor: pointer; min-height: 1.5em; display: inline-block;"
                                  title="Double-click to edit">Loading...</span>
                        </template>
                        <template x-if="editing">
                            <input type="text" class="form-control form-control-sm"
                                   x-model="val"
                                   x-ref="input"
                                   x-init="$nextTick(() => $refs.input.focus())"
                                   @keydown.enter="editing = false"
                                   @keydown.escape="editing = false; val = '{{ cfg.value|e }}'"
                                   @click.outside="editing = false">
                        </template>
                    </td>
                    <td><span class="badge bg-info">{{ cfg.type }}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary"
                                hx-put="/api/v1/config/{{ cfg.key }}"
                                hx-vals='{"value": val, "type": "{{ cfg.type }}", "group": "{{ cfg.group_name }}"}'
                                hx-target="closest tr"
                                hx-swap="outerHTML"
                                @click.prevent="editing = false"
                                title="Save">💾</button>
                        <button class="btn btn-sm btn-outline-danger"
                                hx-delete="/api/v1/config/{{ cfg.key }}"
                                hx-confirm="Reset '{{ cfg.key }}' to default?"
                                hx-target="closest tr"
                                hx-swap="outerHTML"
                                title="Reset">↺</button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    <div class="mt-2 d-flex gap-2">
        <button class="btn btn-danger btn-sm"
                hx-post="/api/v1/config/reset"
                hx-confirm="Reset ALL config values to environment defaults? This cannot be undone."
                hx-target="#config-table"
                hx-swap="innerHTML">Reset All</button>
    </div>
    {% else %}
    <p class="text-muted">No configuration entries found. Config values are read from environment variables.</p>
    {% endif %}
    ```

    Step 6 — Run tests to verify they pass.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py::TestAdminConfig -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - GET /admin/tabs/config-table returns 200 with config rows
    - tab_admin.html has search input that filters config rows by key/group name
    - _config_table.html renders group badge, key, value (double-click to edit), type badge, save/reset buttons
    - Double-clicking value switches to input field; Enter/Escape/blur saves/cancels
    - Save sends PUT /api/v1/config/{key}; Reset sends DELETE /api/v1/config/{key}
    - "Reset All" sends POST /api/v1/config/reset with confirmation
    - Empty state shows helpful message when no configs
  </acceptance_criteria>
  <done>Admin Config tab with inline editing implemented and tested.</done>
</task>

<task type="auto" tdd="true">
  <name>Profile tab + Browse cleanup (per SPA-07, SPA-09)</name>
  <files>kb_server/ui/routes_admin.py, kb_server/ui/templates/admin/tab_profile.html, kb_server/ui/templates/admin/_profile_content.html, kb_server/ui/templates/browse.html, tests/test_admin_ui.py</files>
  <read_first>kb_server/auth/router.py, kb_server/ui/templates/browse.html, kb_server/ui/routes_admin.py</read_first>
  <action>
    Step 1 — Write failing tests in TestProfileTab class:
    `test_profile_content_returns_200` — GET /admin/tabs/profile-content returns 200

    Step 2 — Add profile-content endpoint and doc cleanup endpoints to routes_admin.py:

    ```python
    @app.get("/admin/tabs/profile-content", response_class=HTMLResponse, include_in_schema=False)
    async def admin_profile_content(request: Request):
        """Return profile tab content partial."""
        from kb_server.ui.app import templates
        return templates.TemplateResponse(
            request,
            "admin/_profile_content.html",
            {"request": request},
        )


    @app.delete("/api/v1/documents/{source_file:path}")
    async def delete_document(source_file: str):
        """Delete a document from Qdrant and mark deleted in registry."""
        import sqlite3
        from pathlib import Path
        from kb_server.vector_store import VectorStore
        store = VectorStore()
        await store.connect()
        try:
            await store.delete_by_source(source_file)
        finally:
            await store.close()
        db_path = Path("data/kb_metadata.db")
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            conn.execute(
                "UPDATE files SET status = 'deleted' WHERE path = ?",
                (source_file,),
            )
            conn.commit()
            conn.close()
        return {"status": "deleted", "source_file": source_file}


    @app.post("/api/v1/documents/{source_file:path}/re-ingest")
    async def reingest_document(source_file: str):
        """Re-ingest a document."""
        from ingest.ingest import process_file
        result = await process_file(source_file)
        return {"status": "re-ingested", "source_file": source_file, "result": str(result)}


    @app.post("/api/v1/documents/delete-failed")
    async def delete_failed_documents():
        """Delete all documents with 'failed' status from registry."""
        import sqlite3
        from pathlib import Path
        db_path = Path("data/kb_metadata.db")
        if not db_path.exists():
            return {"status": "ok", "deleted": 0}
        conn = sqlite3.connect(str(db_path))
        cur = conn.execute("DELETE FROM files WHERE status = 'failed'")
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        return {"status": "ok", "deleted": deleted}
    ```

    Step 3 — Create `kb_server/ui/templates/admin/_profile_content.html`:

    ```html
    <div x-data="profilePage()" x-init="initProfile()">
        <div class="row">
            <!-- Account Info Column -->
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-body">
                        <h5 class="card-title">Account</h5>
                        <p><strong>Username:</strong> <span x-text="user.username || 'Loading...'"></span></p>
                        <p><strong>Role:</strong> <span class="badge bg-primary" x-text="user.role"></span></p>
                        <p><strong>Created:</strong> <span x-text="user.created_at ? user.created_at.slice(0, 10) : '...'"></span></p>
                        <div class="d-flex gap-2 mt-3">
                            <button class="btn btn-outline-secondary btn-sm" @click="exportData()">
                                📥 Export My Data
                            </button>
                            <button class="btn btn-outline-danger btn-sm" @click="requestErasure()">
                                🗑️ Request Erasure
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- API Keys Column -->
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-body">
                        <h5 class="card-title">API Keys</h5>
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Prefix</th>
                                        <th>Description</th>
                                        <th>Created</th>
                                        <th>Status</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <template x-for="key in keys" :key="key.id">
                                        <tr>
                                            <td><code x-text="key.prefix"></code></td>
                                            <td x-text="key.description"></td>
                                            <td><small x-text="key.created_at ? key.created_at.slice(0, 10) : ''"></small></td>
                                            <td>
                                                <span class="badge"
                                                      :class="key.is_revoked ? 'bg-danger' : 'bg-success'"
                                                      x-text="key.is_revoked ? 'Revoked' : 'Active'"></span>
                                            </td>
                                            <td>
                                                <button class="btn btn-sm btn-outline-danger"
                                                        @click="revokeKey(key.id)"
                                                        x-show="!key.is_revoked">Revoke</button>
                                            </td>
                                        </tr>
                                    </template>
                                    <tr x-show="keys.length === 0">
                                        <td colspan="5" class="text-muted text-center">No API keys yet.</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        <button class="btn btn-primary btn-sm" @click="generateKey()">Generate New Key</button>

                        <!-- New key display (shown once) -->
                        <div x-show="newKey" class="alert alert-success mt-2" style="display: none;">
                            <strong>New API Key Generated</strong>
                            <p class="mb-1 mt-1"><code x-text="newKey" style="word-break: break-all;"></code></p>
                            <small class="text-danger fw-semibold">This key will only be shown once. Copy it now.</small>
                            <button class="btn btn-sm btn-outline-primary ms-2" @click="copyKey()">📋 Copy</button>
                        </div>

                        <!-- Erasure status -->
                        <div x-show="erasureStatus" class="alert alert-warning mt-2" style="display: none;">
                            Erasure request: <strong x-text="erasureStatus"></strong>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
    function profilePage() {
        return {
            user: { username: '', role: '', created_at: '' },
            keys: [],
            newKey: '',
            erasureStatus: '',

            initProfile() {
                const savedKey = localStorage.getItem('kb_api_key');
                if (!savedKey) return;
                const headers = { 'Authorization': 'Bearer ' + savedKey };
                fetch('/api/v1/users/me', { headers })
                    .then(r => r.json())
                    .then(data => { this.user = data; })
                    .catch(() => {});
                this.loadKeys();
            },

            loadKeys() {
                if (this.user.id) {
                    const headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key') };
                    fetch('/api/v1/api-keys?user_id=' + this.user.id, { headers })
                        .then(r => r.json())
                        .then(data => { this.keys = data; })
                        .catch(() => {});
                }
            },

            generateKey() {
                if (!this.user.id) return;
                const headers = {
                    'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key'),
                    'Content-Type': 'application/json'
                };
                fetch('/api/v1/api-keys', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({ user_id: this.user.id, description: 'Admin SPA key' })
                })
                .then(r => r.json())
                .then(data => {
                    this.newKey = data.raw_key;
                    this.loadKeys();
                    setTimeout(() => { this.newKey = ''; }, 30000);
                })
                .catch(() => {});
            },

            revokeKey(keyId) {
                if (!confirm('Revoke this API key? Applications using this key will lose access immediately.')) return;
                const headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key') };
                fetch('/api/v1/api-keys/' + keyId, { method: 'DELETE', headers })
                    .then(() => this.loadKeys());
            },

            copyKey() {
                navigator.clipboard.writeText(this.newKey).catch(() => {});
            },

            exportData() {
                const headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key') };
                fetch('/api/v1/users/' + this.user.id + '/export', { headers })
                    .then(r => r.json())
                    .then(data => {
                        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'my-data-export.json';
                        a.click();
                        URL.revokeObjectURL(url);
                    })
                    .catch(() => {});
            },

            requestErasure() {
                if (!confirm('Request complete erasure of all your data? This will anonymize your account and revoke all API keys.')) return;
                const headers = { 'Authorization': 'Bearer ' + localStorage.getItem('kb_api_key') };
                fetch('/api/v1/users/' + this.user.id + '/erasure-request', {
                    method: 'POST',
                    headers: headers
                })
                .then(r => r.json())
                .then(data => { this.erasureStatus = data.status; })
                .catch(() => {});
            }
        };
    }
    </script>
    ```

    Step 4 — Update `kb_server/ui/templates/admin/tab_profile.html` (replace placeholder):

    ```html
    <h3>Profile</h3>
    <p class="text-muted">Your account settings and API keys.</p>
    <div id="profile-content"
         hx-get="/admin/tabs/profile-content"
         hx-trigger="load"
         hx-swap="innerHTML">
        <p class="text-muted">Loading profile...</p>
    </div>
    ```

    Step 5 — Add browse cleanup controls to `kb_server/ui/templates/browse.html`:

    Add cleanup toolbar div after the filters card (line ~64, before "Results count"):

    ```html
    <!-- Batch cleanup toolbar (appears when docs selected) -->
    <div id="cleanup-toolbar" class="mb-3" style="display: none;">
        <div class="d-flex align-items-center gap-2">
            <span class="fw-semibold" id="selected-count">0 selected</span>
            <button class="btn btn-danger btn-sm" id="delete-selected-btn"
                    hx-confirm="Delete selected documents? This cannot be undone.">Delete</button>
            <button class="btn btn-warning btn-sm" id="reingest-selected-btn">Re-ingest</button>
            <button class="btn btn-outline-danger btn-sm" id="delete-failed-btn"
                    hx-post="/api/v1/documents/delete-failed"
                    hx-confirm="Delete all failed documents?"
                    hx-target="#cleanup-toolbar">Delete Failed</button>
        </div>
    </div>
    ```

    Modify the `<thead>` to add checkbox column:

    ```html
                <tr>
                    <th><input type="checkbox" id="select-all" onchange="toggleSelectAll(this)"></th>
                    <th>ID</th>
                    <th>Source File</th>
                    <th>Product</th>
                    <th>Type</th>
                    <th>Version</th>
                    <th>Status</th>
                    <th>Chunks</th>
                    <th>Actions</th>
                </tr>
    ```

    Add checkbox to each `<tr>` in the documents loop (after `<tr>` line, first `<td>`):

    ```html
                    <td><input type="checkbox" class="doc-checkbox" value="{{ doc.source_file }}" onchange="updateToolbar()"></td>
    ```

    Replace the Actions column `<td>` content (the single "View" button) with dropdown:

    ```html
                    <td>
                        <div class="dropdown">
                            <button class="btn btn-sm btn-outline-secondary dropdown-toggle"
                                    data-bs-toggle="dropdown">Actions</button>
                            <ul class="dropdown-menu">
                                <li><a class="dropdown-item" href="/ui/document/{{ doc.id }}">View</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item" href="#"
                                       hx-delete="/api/v1/documents/{{ doc.source_file }}"
                                       hx-confirm="Delete this document? This action cannot be undone."
                                       hx-target="closest tr"
                                       hx-swap="outerHTML">Delete</a></li>
                                <li><a class="dropdown-item" href="#"
                                       hx-post="/api/v1/documents/{{ doc.source_file }}/re-ingest"
                                       hx-target="closest tr"
                                       hx-swap="outerHTML">Re-ingest</a></li>
                            </ul>
                        </div>
                    </td>
    ```

    Add the cleanup JavaScript in an extra_scripts block:

    ```html
    {% block extra_scripts %}
    {{ super() }}
    <script nonce="{{ request.state.csp_nonce }}">
    function toggleSelectAll(source) {
        document.querySelectorAll('.doc-checkbox').forEach(cb => cb.checked = source.checked);
        updateToolbar();
    }
    function updateToolbar() {
        const checked = document.querySelectorAll('.doc-checkbox:checked');
        const toolbar = document.getElementById('cleanup-toolbar');
        const count = document.getElementById('selected-count');
        if (checked.length > 0) {
            toolbar.style.display = 'block';
            count.textContent = checked.length + ' selected';
        } else {
            toolbar.style.display = 'none';
        }
    }
    </script>
    {% endblock %}
    ```

    Step 6 — Run all admin UI tests.
  </action>
  <verify>
    <automated>cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - GET /admin/tabs/profile-content returns 200 with profile content
    - Profile template shows account info (username, role, created) via Alpine.js
    - API keys table loads via fetch(/api/v1/api-keys) with Bearer token
    - Generate New Key sends POST /api/v1/api-keys, displays raw_key once
    - Revoke sends DELETE /api/v1/api-keys/{id} with confirmation
    - GDPR Export downloads JSON via blob URL
    - Erasure request sends POST to /api/v1/users/{id}/erasure-request
    - DELETE /api/v1/documents/{source_file} deletes from Qdrant + marks deleted in registry
    - POST /api/v1/documents/{source_file}/re-ingest calls process_file
    - browse.html has checkbox column, select-all header checkbox
    - Cleanup toolbar appears when checkboxes checked (Delete, Re-ingest, Delete Failed)
    - Per-document Actions dropdown with View, Delete, Re-ingest
  </acceptance_criteria>
  <done>Profile tab with API key/GDPR features and document browse cleanup implemented and tested.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| HTMX → /api/v1/documents/* | Document deletion/re-ingest from browser |
| HTMX → /admin/tabs/config-table | Config value display with inline editing |
| Alpine.js fetch → /api/v1/api-keys | API key CRUD from profile tab |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-28c-06 | Tampering | Config PUT/DELETE via HTMX | accept | No auth on config API per project scope (internal-only deployment) |
| T-28c-07 | Spoofing | Document DELETE without auth | accept | No auth on cleanup endpoints; internal-only deployment assumed |
| T-28c-08 | Information Disclosure | Health component details in monitor lights | accept | Internal admin UI; component status not sensitive |
| T-28c-09 | Denial of Service | Rapid monitor-lights polling every 30s | accept | 30s interval is low-frequency; single endpoint, no DB query |
</threat_model>

<verification>
### Per-Task Verification
Each task has automated test verification. Run all admin UI tests:

```bash
cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -20
```

### Manual Checks
1. Browse documents page shows checkbox column and Actions dropdown
2. Checkboxes enable batch cleanup toolbar (Delete, Re-ingest, Delete Failed)
3. Monitor lights show 7 component colored badges with latency and details toggle
4. Config table renders group badges, editable values (double-click), save/reset buttons
5. Profile tab loads user info, API keys table, Generate New Key shows raw key once

### Regression Check
```bash
cd /home/admin/kb-rag-mcp && python -m pytest -x --timeout=60 2>&1 | tail -10
```
</verification>

<success_criteria>
- Monitor lights bar auto-refreshes every 30s with 7 component health cards
- Admin Config tab shows config table grouped by category with inline editing
- Profile tab loads user info, manages API keys, and provides GDPR export/erasure
- Document browse has checkbox selection, batch cleanup toolbar, per-doc action dropdown
- All test_admin_ui.py tests pass; no regressions in full suite
</success_criteria>

<output>
  <file path="kb_server/ui/routes_admin.py" summary="Added monitor-lights, config-table, profile-content endpoints + document cleanup API" />
  <file path="kb_server/ui/templates/admin/_monitor_lights.html" summary="7 health component cards with colored badges and details toggle" />
  <file path="kb_server/ui/templates/admin/tab_monitoring.html" summary="Updated with HTMX load and every-30s refresh for monitor lights" />
  <file path="kb_server/ui/templates/admin/tab_admin.html" summary="Updated with search input and config-table HTMX load" />
  <file path="kb_server/ui/templates/admin/_config_table.html" summary="Config table with Alpine.js inline editing, search filter, reset" />
  <file path="kb_server/ui/templates/admin/tab_profile.html" summary="Updated with profile-content HTMX load" />
  <file path="kb_server/ui/templates/admin/_profile_content.html" summary="Profile tab with Alpine.js API key management and GDPR features" />
  <file path="kb_server/ui/templates/browse.html" summary="Added checkbox column, cleanup toolbar, per-doc Actions dropdown" />
  <file path="tests/test_admin_ui.py" summary="Extended with monitor lights, config, profile, cleanup tests" />
</output>
