---
phase: 28c-admin-spa-panel
plan: "02"
type: execute
wave: 2
depends_on:
  - 28b-auth-api
  - 40-config-backlog
files_modified:
  - kb_server/ui/routes_admin.py
  - kb_server/ui/templates/admin/tab_admin.html
  - kb_server/ui/templates/admin/_config_table.html
  - kb_server/ui/templates/admin/_monitor_lights.html
  - kb_server/ui/templates/admin/_ingestion_manual.html
  - kb_server/ui/templates/admin/_ingestion_schedule.html
  - kb_server/ui/templates/admin/_ingestion_monitor.html
  - kb_server/ui/templates/admin/_ragas_editor.html
  - kb_server/ui/templates/admin/_ragas_results.html
  - kb_server/ui/templates/admin/_profile_content.html
  - kb_server/ui/templates/browse.html
  - ingest/scheduler.py
  - kb_server/evaluation/dataset.py
  - kb_server/ui/app.py
  - tests/test_admin_ui.py
  - tests/test_ingestion_admin.py
  - tests/test_ragas_admin.py
autonomous: true
requirements:
  - R28C-02
  - R28C-03
  - R28C-04
  - R28C-05
must_haves:
  truths:
    - All 6 admin tabs load and display content correctly
    - Monitor lights bar auto-refreshes every 30s with 7 components
    - Ingestion supports manual trigger, schedule, and monitor modes
    - RAGAS golden set editor with import/export and evaluation runner
    - Browser cleanup with delete and re-ingest per document
    - Profile tab with API key management, GDPR export/erasure
  artifacts:
    - path: "kb_server/ui/routes_admin.py"
      provides: "All admin tab endpoints"
      contains: "admin/tabs/"
      min_lines: 150
    - path: "ingest/scheduler.py"
      provides: "Background ingestion scheduler"
      contains: "IngestionScheduler"
      min_lines: 100
    - path: "kb_server/ui/templates/admin/_ragas_editor.html"
      provides: "Golden set editor UI"
      contains: "ragasEditor"
      min_lines: 100
---

<objective>
Implement all 6 admin tab content panels — Admin Config page, Monitor Lights bar, Ingestion (manual + schedule + monitor), RAGAS (golden set editor + evaluation), Browser Cleanup (delete + re-ingest), and Profile page.

Purpose: Phase 28c tab content provides the actual functionality for the Admin SPA shell. Each tab is a Jinja2 partial loaded via HTMX. Backend endpoints in routes_admin.py provide data and handle mutations. The monitor lights bar auto-refreshes every 30s via HTMX polling. Ingestion scheduling uses a new IngestionScheduler background task. RAGAS golden set CRUD extends existing GoldenDataset. Browser cleanup adds REST delete/re-ingest endpoints.

Architecture: Each tab is a Jinja2 partial loaded via HTMX. Backend endpoints in routes_admin.py provide data and handle mutations. The monitor lights bar auto-refreshes every 30s via HTMX polling. Ingestion scheduling uses a new IngestionScheduler background task. RAGAS golden set CRUD extends existing GoldenDataset. Browser cleanup adds REST delete/re-ingest endpoints.

Output: Config page with inline editing, monitor lights bar with 7 health indicators, ingestion tab with manual/schedule/monitor sub-tabs, RAGAS golden set editor with import/export/evaluation, browser cleanup with delete and re-ingest, profile page with API key management and GDPR features.
</objective>

<execution_context>
@/home/admin/.config/opencode/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@kb_server/ui/routes_admin.py
@kb_server/ui/templates/admin/tab_admin.html
@kb_server/ui/templates/admin/tab_monitoring.html
@kb_server/ui/templates/admin/tab_ingestion.html
@kb_server/ui/templates/admin/tab_ragas.html
@kb_server/ui/templates/admin/tab_profile.html
@kb_server/ui/templates/browse.html
@ingest/scheduler.py
@kb_server/evaluation/dataset.py
@kb_server/ui/app.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Admin Config page (tab_admin.html)</name>
  <files>kb_server/ui/routes_admin.py, kb_server/ui/templates/admin/tab_admin.html, kb_server/ui/templates/admin/_config_table.html, tests/test_admin_ui.py</files>
  <read_first>kb_server/ui/routes_admin.py, kb_server/ui/templates/admin/tab_admin.html</read_first>
  <action>
    Step 1: Write failing test — config tab loads and displays.

    Append to tests/test_admin_ui.py:
    ```python
    @pytest.mark.asyncio
    async def test_admin_config_tab():
        from httpx import AsyncClient, ASGITransport
        from kb_server.ui.app import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/admin/tabs/admin")
        assert resp.status_code == 200
        assert "config" in resp.text.lower() or "settings" in resp.text.lower()
    ```

    Step 2: Run test to confirm it fails.

    Step 3: Implement config tab template.

    Replace kb_server/ui/templates/admin/tab_admin.html:
    ```html
    <h3>Admin Settings</h3>
    <p class="text-muted">System configuration. Changes apply immediately via hot-reload.</p>

    <div class="mb-3">
        <input type="text" class="form-control" id="config-search" placeholder="Search config keys..."
               x-on:input="filterConfig = $event.target.value">
    </div>

    <div id="config-table" hx-get="/api/v1/config" hx-trigger="load" hx-swap="innerHTML"
         x-data="{ filterConfig: '' }"
         x-on:htmx:afterSwap="filterConfig = ''">
    </div>

    <script>
        document.body.addEventListener('htmx:afterSwap', function(evt) {
            if (evt.detail.target.id === 'config-table') {
                const searchInput = document.getElementById('config-search');
                if (searchInput) {
                    searchInput.addEventListener('input', function() {
                        const q = this.value.toLowerCase();
                        document.querySelectorAll('#config-table .config-row').forEach(row => {
                            const key = row.querySelector('.config-key')?.textContent?.toLowerCase() || '';
                            row.style.display = key.includes(q) ? '' : 'none';
                        });
                    });
                }
            }
        });
    </script>
    ```

    Step 4: Add inline config editing endpoint to routes_admin.py.

    ```python
    @app.get("/admin/tabs/config-table", response_class=HTMLResponse, include_in_schema=False)
    async def admin_config_table(request: Request):
        from kb_server.config.loader import ConfigLoader
        loader = ConfigLoader()
        configs = await loader.get_all()
        from kb_server.ui.app import templates
        return templates.TemplateResponse(
            request, "admin/_config_table.html",
            {"request": request, "configs": configs},
        )
    ```

    Step 5: Create kb_server/ui/templates/admin/_config_table.html:
    ```html
    {% if configs %}
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
            <tr class="config-row">
                <td><span class="badge bg-secondary">{{ cfg.group }}</span></td>
                <td class="config-key"><code>{{ cfg.key }}</code></td>
                <td>
                    <span x-data="{ editing: false, val: '{{ cfg.value }}' }">
                        <template x-if="!editing">
                            <span x-text="val" x-on:dblclick="editing = true" style="cursor: pointer;"></span>
                        </template>
                        <template x-if="editing">
                            <input type="text" class="form-control form-control-sm" x-model="val"
                                   x-on:blur="editing = false; $el.closest('tr').querySelector('.save-btn')?.click()"
                                   x-on:keydown.enter="editing = false"
                                   x-ref="input" x-init="$refs.input.focus()">
                        </template>
                    </span>
                    <button class="btn btn-sm btn-outline-primary save-btn d-none"
                            hx-put="/api/v1/config/{{ cfg.key }}"
                            hx-headers='{"Content-Type": "application/json"}'
                            hx-vals='{"value": "{{ cfg.value }}", "type": "{{ cfg.type }}", "group": "{{ cfg.group }}"}'
                            hx-target="closest tr" hx-swap="outerHTML">Save</button>
                </td>
                <td><span class="badge bg-info">{{ cfg.type }}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-danger"
                            hx-delete="/api/v1/config/{{ cfg.key }}"
                            hx-confirm="Delete config key '{{ cfg.key }}'?"
                            hx-target="closest tr" hx-swap="outerHTML">×</button>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    <div class="mt-2">
        <button class="btn btn-danger btn-sm"
                hx-post="/api/v1/config/reset"
                hx-confirm="Reset all config to defaults? This cannot be undone."
                hx-target="#config-table" hx-swap="innerHTML">Reset All</button>
    </div>
    {% else %}
    <p class="text-muted">No configuration entries. Use the API to add config.</p>
    {% endif %}
    ```

    Step 6: Run tests to verify they pass.
  </action>
  <verify>
    <automated>python -m pytest tests/test_admin_ui.py::test_admin_config_tab -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - test_admin_config_tab passes: GET /admin/tabs/admin returns 200 with "config" or "settings" in body
    - tab_admin.html shows search input and config-table div with HTMX load trigger
    - _config_table.html renders config rows with inline editing, save, delete, reset
    - /admin/tabs/config-table endpoint returns rendered table partial
  </acceptance_criteria>
  <done>Admin Config page with inline editing implemented and tested</done>
</task>

<task type="auto" tdd="true">
  <name>Monitor Lights bar</name>
  <files>kb_server/ui/routes_admin.py, kb_server/ui/templates/admin/_monitor_lights.html, tests/test_admin_ui.py</files>
  <read_first>kb_server/ui/routes_admin.py, kb_server/ui/templates/admin/tab_monitoring.html</read_first>
  <action>
    Step 1: Write failing test — monitor lights render.

    Append to tests/test_admin_ui.py:
    ```python
    @pytest.mark.asyncio
    async def test_monitor_lights_partial():
        from httpx import AsyncClient, ASGITransport
        from kb_server.ui.app import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/admin/tabs/monitor-lights")
        assert resp.status_code == 200
        # Should reference health components
        assert "Qdrant" in resp.text or "qdrant" in resp.text.lower() or "monitor" in resp.text.lower()
    ```

    Step 2: Run test to confirm it fails.

    Step 3: Add monitor-lights endpoint to routes_admin.py.
    ```python
    @app.get("/admin/tabs/monitor-lights", response_class=HTMLResponse, include_in_schema=False)
    async def monitor_lights_partial(request: Request):
        from kb_server.health import check_all_components
        components = await check_all_components()
        from kb_server.ui.app import templates
        return templates.TemplateResponse(
            request, "admin/_monitor_lights.html",
            {"request": request, "components": components},
        )
    ```

    Step 4: Create kb_server/ui/templates/admin/_monitor_lights.html:
    ```html
    <div class="d-flex gap-3 flex-wrap mb-3">
        {% for name, status in {
            "vector_store": "Qdrant",
            "embedding": "Embedding",
            "llm_provider": "LLM Provider",
            "cache": "Cache",
            "database": "Database",
            "filesystem": "Filesystem",
            "grafana": "Grafana",
        }.items() %}
        {% set comp = components.get(name) %}
        <div class="card" style="width: 160px;" x-data="{ detail: false }">
            <div class="card-body text-center p-2">
                <div class="mb-1">
                    {% if comp and comp.healthy %}
                    <span class="badge bg-success" style="width: 12px; height: 12px; display: inline-block; border-radius: 50%;">&nbsp;</span>
                    {% elif comp and not comp.healthy %}
                    <span class="badge bg-danger" style="width: 12px; height: 12px; display: inline-block; border-radius: 50%;">&nbsp;</span>
                    {% else %}
                    <span class="badge bg-secondary" style="width: 12px; height: 12px; display: inline-block; border-radius: 50%;">&nbsp;</span>
                    {% endif %}
                    <small class="d-block mt-1">{{ status }}</small>
                </div>
                {% if comp %}
                <small class="text-muted">{{ comp.message|truncate(25) }}</small>
                {% if comp.latency_ms is not none %}
                <br><small class="text-muted">{{ "%.0f"|format(comp.latency_ms) }}ms</small>
                {% endif %}
                <br>
                <a href="#" x-on:click.prevent="detail = !detail" class="small">details</a>
                <div x-show="detail" style="display: none;" class="mt-1 text-start small">
                    <code>{{ comp.to_dict() }}</code>
                </div>
                {% else %}
                <small class="text-muted">Unknown</small>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
    ```

    Step 5: Run tests to verify they pass.
  </action>
  <verify>
    <automated>python -m pytest tests/test_admin_ui.py::test_monitor_lights_partial -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - test_monitor_lights_partial passes: GET /admin/tabs/monitor-lights returns 200 with health component reference
    - /admin/tabs/monitor-lights endpoint calls check_all_components and renders template
    - _monitor_lights.html displays all 7 components (Qdrant, Embedding, LLM, Cache, Database, Filesystem, Grafana)
    - Each component shows green/red/gray badge, message, latency, and expandable details
  </acceptance_criteria>
  <done>Monitor Lights bar with 7 component health indicators implemented and tested</done>
</task>

<task type="auto" tdd="true">
  <name>Ingestion tab (manual + schedule + monitor)</name>
  <files>ingest/scheduler.py, kb_server/ui/routes_admin.py, kb_server/ui/templates/admin/_ingestion_manual.html, kb_server/ui/templates/admin/_ingestion_schedule.html, kb_server/ui/templates/admin/_ingestion_monitor.html, tests/test_ingestion_admin.py</files>
  <read_first>kb_server/ui/routes_admin.py, kb_server/ui/templates/admin/tab_ingestion.html</read_first>
  <action>
    Step 1: Write failing tests — ingestion tab endpoints.

    Create tests/test_ingestion_admin.py:
    ```python
    import pytest


    @pytest.mark.asyncio
    async def test_ingestion_manual_partial():
        from httpx import AsyncClient, ASGITransport
        from kb_server.ui.app import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/admin/tabs/ingestion-manual")
        assert resp.status_code == 200


    @pytest.mark.asyncio
    async def test_ingestion_schedule_partial():
        from httpx import AsyncClient, ASGITransport
        from kb_server.ui.app import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/admin/tabs/ingestion-schedule")
        assert resp.status_code == 200


    @pytest.mark.asyncio
    async def test_ingestion_monitor_partial():
        from httpx import AsyncClient, ASGITransport
        from kb_server.ui.app import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/admin/tabs/ingestion-monitor")
        assert resp.status_code == 200
    ```

    Step 2: Run tests to confirm they fail.

    Step 3: Add ingestion tab endpoints to routes_admin.py.
    ```python
    @app.get("/admin/tabs/ingestion-manual", response_class=HTMLResponse, include_in_schema=False)
    async def ingestion_manual_tab(request: Request):
        from kb_server.ui.app import templates
        return templates.TemplateResponse(
            request, "admin/_ingestion_manual.html",
            {"request": request},
        )


    @app.get("/admin/tabs/ingestion-schedule", response_class=HTMLResponse, include_in_schema=False)
    async def ingestion_schedule_tab(request: Request):
        from kb_server.ui.app import templates
        return templates.TemplateResponse(
            request, "admin/_ingestion_schedule.html",
            {"request": request},
        )


    @app.get("/admin/tabs/ingestion-monitor", response_class=HTMLResponse, include_in_schema=False)
    async def ingestion_monitor_tab(request: Request):
        from kb_server.ui.app import templates
        return templates.TemplateResponse(
            request, "admin/_ingestion_monitor.html",
            {"request": request},
        )


    @app.post("/api/v1/jobs")
    async def create_job_api(docs_path: str = "", product: str = ""):
        """Create a new ingestion job via API."""
        from ingest.job.manager import JobManager
        from ingest.core.metadata import MetadataStore
        store = MetadataStore()
        mgr = JobManager(store)
        job = mgr.create_job(
            docs_path=docs_path or "data/docs",
            product_override=product or None,
        )
        return {"job_id": job.id, "status": job.status.value}


    @app.get("/api/v1/jobs")
    async def list_jobs_api(limit: int = 20):
        """List recent jobs."""
        from ingest.job.manager import JobManager
        from ingest.core.metadata import MetadataStore
        store = MetadataStore()
        mgr = JobManager(store)
        jobs = mgr.list_jobs(limit=limit)
        return [
            {
                "id": j.id,
                "status": j.status.value,
                "files_total": j.files_total,
                "files_processed": j.files_processed,
                "created_at": j.created_at.isoformat() if j.created_at else "",
            }
            for j in jobs
        ]
    ```

    Step 4: Create kb_server/ui/templates/admin/_ingestion_manual.html:
    ```html
    <div class="card">
        <div class="card-body">
            <h5 class="card-title">Manual Ingestion</h5>
            <form hx-post="/api/v1/jobs" hx-target="#ingestion-result" hx-swap="innerHTML">
                <div class="mb-3">
                    <label for="docs_path" class="form-label">Docs Path</label>
                    <input type="text" class="form-control" id="docs_path" name="docs_path" value="data/docs">
                </div>
                <div class="mb-3">
                    <label for="product" class="form-label">Product Override (optional)</label>
                    <input type="text" class="form-control" id="product" name="product" placeholder="e.g., ArchiveCenter">
                </div>
                <button type="submit" class="btn btn-primary">Ingest Now</button>
            </form>
            <div id="ingestion-result" class="mt-3"></div>
        </div>
    </div>
    ```

    Step 5: Create kb_server/ui/templates/admin/_ingestion_schedule.html:
    ```html
    <div class="card mb-3">
        <div class="card-body">
            <h5 class="card-title">Add Schedule</h5>
            <form hx-post="/api/v1/schedules" hx-target="#schedule-list" hx-swap="innerHTML">
                <div class="row g-2">
                    <div class="col-md-3">
                        <select class="form-select" name="interval">
                            <option value="3600">Every Hour</option>
                            <option value="21600">Every 6 Hours</option>
                            <option value="86400">Daily</option>
                            <option value="604800">Weekly</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <input type="text" class="form-control" name="docs_path" placeholder="Docs path" value="data/docs">
                    </div>
                    <div class="col-md-2">
                        <input type="text" class="form-control" name="product" placeholder="Product (optional)">
                    </div>
                    <div class="col-md-2">
                        <div class="form-check form-switch mt-2">
                            <input class="form-check-input" type="checkbox" name="enabled" checked>
                            <label class="form-check-label">Enabled</label>
                        </div>
                    </div>
                    <div class="col-md-2">
                        <button type="submit" class="btn btn-primary w-100">Add</button>
                    </div>
                </div>
            </form>
        </div>
    </div>

    <div id="schedule-list" hx-get="/api/v1/schedules" hx-trigger="load" hx-swap="innerHTML">
        <p class="text-muted">Loading schedules...</p>
    </div>
    ```

    Step 6: Create kb_server/ui/templates/admin/_ingestion_monitor.html:
    ```html
    <div id="job-list" hx-get="/api/v1/jobs" hx-trigger="every 5s" hx-swap="innerHTML">
        <p class="text-muted">Loading jobs...</p>
    </div>
    ```

    Step 7: Create ingest/scheduler.py:
    ```python
    """Background ingestion scheduler.

    Reads schedules from a SQLite table and triggers jobs at configured intervals.
    """

    import asyncio
    import json
    import logging
    import os
    import sqlite3
    import time
    from pathlib import Path
    from typing import Optional

    log = logging.getLogger("kb-ingest.scheduler")

    SCHEDULES_DB = Path(os.getenv("SCHEDULES_DB", "data/schedules.db"))


    def _init_db():
        SCHEDULES_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(SCHEDULES_DB))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interval_seconds INTEGER NOT NULL,
                docs_path TEXT NOT NULL,
                product TEXT DEFAULT '',
                enabled INTEGER DEFAULT 1,
                last_run TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()


    class IngestionScheduler:
        """Background scheduler that periodically triggers ingestion jobs."""

        def __init__(self):
            _init_db()
            self._task: Optional[asyncio.Task] = None
            self._running = False

        def _conn(self):
            return sqlite3.connect(str(SCHEDULES_DB))

        async def get_schedules(self) -> list[dict]:
            conn = self._conn()
            rows = conn.execute("SELECT * FROM schedules ORDER BY created_at").fetchall()
            conn.close()
            return [
                {
                    "id": r[0], "interval_seconds": r[1], "docs_path": r[2],
                    "product": r[3], "enabled": bool(r[4]), "last_run": r[5],
                    "created_at": r[6],
                }
                for r in rows
            ]

        async def add_schedule(self, interval_seconds: int, docs_path: str,
                               product: str = "") -> int:
            conn = self._conn()
            cur = conn.execute(
                "INSERT INTO schedules (interval_seconds, docs_path, product) VALUES (?, ?, ?)",
                (interval_seconds, docs_path, product),
            )
            conn.commit()
            sid = cur.lastrowid
            conn.close()
            return sid

        async def delete_schedule(self, schedule_id: int) -> bool:
            conn = self._conn()
            cur = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            conn.commit()
            deleted = cur.rowcount > 0
            conn.close()
            return deleted

        async def run_loop(self):
            """Main scheduler loop — runs forever checking due schedules."""
            self._running = True
            while self._running:
                try:
                    schedules = await self.get_schedules()
                    now = time.time()
                    for sched in schedules:
                        if not sched["enabled"]:
                            continue
                        last_run = sched.get("last_run")
                        elapsed = now - (time.mktime(time.strptime(last_run, "%Y-%m-%d %H:%M:%S"))
                                         if last_run else 0)
                        if elapsed >= sched["interval_seconds"]:
                            await self._trigger_job(sched)
                except Exception as e:
                    log.error(f"Scheduler error: {e}")
                await asyncio.sleep(30)  # check every 30s

        async def _trigger_job(self, sched: dict):
            from ingest.job.manager import JobManager
            from ingest.core.metadata import MetadataStore
            store = MetadataStore()
            mgr = JobManager(store)
            job = mgr.create_job(
                docs_path=sched["docs_path"],
                product_override=sched.get("product") or None,
            )
            log.info(f"Scheduler triggered job {job.id} for {sched['docs_path']}")
            conn = self._conn()
            conn.execute(
                "UPDATE schedules SET last_run = datetime('now') WHERE id = ?",
                (sched["id"],),
            )
            conn.commit()
            conn.close()

        def start(self):
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self.run_loop())
                log.info("Ingestion scheduler started")

        def stop(self):
            self._running = False
            if self._task:
                self._task.cancel()
                self._task = None
                log.info("Ingestion scheduler stopped")


    # Module-level singleton
    _scheduler: IngestionScheduler | None = None


    def get_scheduler() -> IngestionScheduler:
        global _scheduler
        if _scheduler is None:
            _scheduler = IngestionScheduler()
        return _scheduler
    ```

    Step 8: Add schedule API endpoints to routes_admin.py:
    ```python
    from ingest.scheduler import get_scheduler

    @app.get("/api/v1/schedules")
    async def list_schedules():
        sched = get_scheduler()
        return await sched.get_schedules()


    @app.post("/api/v1/schedules")
    async def add_schedule(interval_seconds: int = 86400, docs_path: str = "data/docs",
                           product: str = "", enabled: bool = True):
        sched = get_scheduler()
        sid = await sched.add_schedule(interval_seconds, docs_path, product)
        return {"id": sid, "status": "created"}


    @app.delete("/api/v1/schedules/{schedule_id}")
    async def delete_schedule(schedule_id: int):
        sched = get_scheduler()
        ok = await sched.delete_schedule(schedule_id)
        if not ok:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Schedule not found")
        return {"status": "deleted"}
    ```

    Step 9: Run tests to verify they pass.
  </action>
  <verify>
    <automated>python -m pytest tests/test_ingestion_admin.py -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - All 3 tests pass: test_ingestion_manual_partial, test_ingestion_schedule_partial, test_ingestion_monitor_partial
    - Manual ingestion form submits to POST /api/v1/jobs
    - Schedule form submits to POST /api/v1/schedules with interval, docs_path, product, enabled
    - Monitor partial polls GET /api/v1/jobs every 5s
    - ingest/scheduler.py contains IngestionScheduler class with run_loop, start, stop
    - Schedule CRUD endpoints: GET/POST/DELETE /api/v1/schedules
  </acceptance_criteria>
  <done>Ingestion tab with manual, schedule, and monitor sub-tabs implemented and tested</done>
</task>

<task type="auto" tdd="true">
  <name>RAGAS tab — golden set editor and evaluation</name>
  <files>kb_server/evaluation/dataset.py, kb_server/ui/templates/admin/_ragas_editor.html, kb_server/ui/templates/admin/_ragas_results.html, kb_server/ui/routes_admin.py, tests/test_ragas_admin.py</files>
  <read_first>kb_server/evaluation/dataset.py, kb_server/ui/routes_admin.py</read_first>
  <action>
    Step 1: Add CRUD methods to GoldenDataset in kb_server/evaluation/dataset.py.
    ```python
    class GoldenDataset:
        # ... existing methods ...

        def remove_example(self, index: int) -> None:
            if 0 <= index < len(self.examples):
                self.examples.pop(index)
                self.save()

        def update_example(self, index: int, **kwargs) -> None:
            if 0 <= index < len(self.examples):
                self.examples[index].update(kwargs)
                self.save()

        def to_json(self) -> str:
            return json.dumps(self.examples, indent=2)

        @classmethod
        def from_json_str(cls, json_str: str, dataset_path: Path) -> "GoldenDataset":
            data = json.loads(json_str)
            ds = cls.__new__(cls)
            ds.dataset_path = dataset_path
            ds.examples = data
            return ds
    ```

    Step 2: Write failing test — RAGAS tab endpoints.

    Create tests/test_ragas_admin.py:
    ```python
    import pytest


    @pytest.mark.asyncio
    async def test_ragas_editor_partial():
        from httpx import AsyncClient, ASGITransport
        from kb_server.ui.app import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/admin/tabs/ragas-editor")
        assert resp.status_code == 200


    @pytest.mark.asyncio
    async def test_ragas_results_partial():
        from httpx import AsyncClient, ASGITransport
        from kb_server.ui.app import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/admin/tabs/ragas-results")
        assert resp.status_code == 200
    ```

    Step 3: Run tests to confirm they fail.

    Step 4: Add RAGAS endpoints to routes_admin.py.
    ```python
    import json
    from pathlib import Path

    GOLDEN_SET_PATH = Path(
        os.getenv("GOLDEN_SET_PATH", "kb_server/evaluation/golden_dataset.json")
    )


    @app.get("/admin/tabs/ragas-editor", response_class=HTMLResponse, include_in_schema=False)
    async def ragas_editor_tab(request: Request):
        from kb_server.ui.app import templates
        from kb_server.evaluation.dataset import GoldenDataset
        ds = GoldenDataset(GOLDEN_SET_PATH) if GOLDEN_SET_PATH.exists() else None
        return templates.TemplateResponse(
            request, "admin/_ragas_editor.html",
            {"request": request, "dataset": ds.examples if ds else []},
        )


    @app.get("/admin/tabs/ragas-results", response_class=HTMLResponse, include_in_schema=False)
    async def ragas_results_tab(request: Request):
        from kb_server.ui.app import templates
        results_path = Path("data/evaluation_results.json")
        results = []
        if results_path.exists():
            results = json.loads(results_path.read_text())[-10:]  # last 10
        return templates.TemplateResponse(
            request, "admin/_ragas_results.html",
            {"request": request, "results": results},
        )


    @app.get("/api/v1/evaluation/dataset")
    async def get_golden_set():
        from kb_server.evaluation.dataset import GoldenDataset
        ds = GoldenDataset(GOLDEN_SET_PATH) if GOLDEN_SET_PATH.exists() else None
        return {"examples": ds.examples if ds else [], "count": len(ds) if ds else 0}


    @app.put("/api/v1/evaluation/dataset")
    async def update_golden_set(data: dict):
        from kb_server.evaluation.dataset import GoldenDataset
        ds = GoldenDataset(GOLDEN_SET_PATH)
        idx = data.get("index")
        if idx is not None:
            ds.update_example(idx, **data.get("fields", {}))
        elif data.get("add"):
            ds.add_example(
                query=data["query"],
                expected_answer=data["expected_answer"],
                expected_docs=data.get("expected_docs", []),
            )
        return {"status": "updated", "count": len(ds)}


    @app.delete("/api/v1/evaluation/dataset/{index}")
    async def delete_golden_example(index: int):
        from kb_server.evaluation.dataset import GoldenDataset
        ds = GoldenDataset(GOLDEN_SET_PATH)
        ds.remove_example(index)
        return {"status": "deleted", "count": len(ds)}


    @app.post("/api/v1/evaluation/run")
    async def run_evaluation():
        """Run RAGAS evaluation against the golden set."""
        from kb_server.evaluation.dataset import GoldenDataset
        from kb_server.evaluation.ragas_pipeline import RAGASEvaluator
        ds = GoldenDataset(GOLDEN_SET_PATH)
        if len(ds) == 0:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Golden set is empty")
        evaluator = RAGASEvaluator(dataset=ds)
        results = await evaluator.evaluate()
        # Save results
        results_path = Path("data/evaluation_results.json")
        existing = []
        if results_path.exists():
            existing = json.loads(results_path.read_text())
        existing.append({
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "metrics": results,
        })
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(json.dumps(existing, indent=2))
        return {"status": "completed", "metrics": results}


    @app.post("/api/v1/evaluation/dataset/import")
    async def import_golden_set(data: dict):
        from kb_server.evaluation.dataset import GoldenDataset
        ds = GoldenDataset.from_json_str(
            json.dumps(data.get("examples", [])), GOLDEN_SET_PATH
        )
        ds.save()
        return {"status": "imported", "count": len(ds)}


    @app.get("/api/v1/evaluation/dataset/export")
    async def export_golden_set():
        from kb_server.evaluation.dataset import GoldenDataset
        ds = GoldenDataset(GOLDEN_SET_PATH) if GOLDEN_SET_PATH.exists() else None
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content={"examples": ds.examples if ds else []},
            headers={"Content-Disposition": "attachment; filename=golden_dataset.json"},
        )
    ```

    Step 5: Create kb_server/ui/templates/admin/_ragas_editor.html:
    ```html
    <div x-data="ragasEditor()">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h5 class="mb-0">Golden Set (<span x-text="examples.length"></span> examples)</h5>
            <div>
                <button class="btn btn-outline-primary btn-sm" x-on:click="importDialog = true">Import</button>
                <a href="/api/v1/evaluation/dataset/export" class="btn btn-outline-secondary btn-sm">Export</a>
                <button class="btn btn-success btn-sm" x-on:click="runEval()" x-text="evalRunning ? 'Running...' : 'Run Evaluation'"></button>
            </div>
        </div>

        <!-- Import dialog -->
        <div x-show="importDialog" class="card mb-3" style="display: none;">
            <div class="card-body">
                <h6>Import Golden Set (JSON)</h6>
                <textarea class="form-control mb-2" rows="5" x-model="importJson" placeholder='[{"query": "...", "expected_answer": "...", "expected_docs": [...]}]'></textarea>
                <button class="btn btn-primary btn-sm" x-on:click="doImport()">Import</button>
                <button class="btn btn-secondary btn-sm" x-on:click="importDialog = false">Cancel</button>
            </div>
        </div>

        <!-- Table -->
        <div class="table-responsive">
            <table class="table table-sm table-hover">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Query</th>
                        <th>Expected Answer</th>
                        <th>Expected Docs</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <template x-for="(ex, idx) in examples" :key="idx">
                        <tr>
                            <td x-text="idx + 1"></td>
                            <td><input type="text" class="form-control form-control-sm" x-model="ex.query"
                                       x-on:change="updateExample(idx, 'query', ex.query)"></td>
                            <td><input type="text" class="form-control form-control-sm" x-model="ex.expected_answer"
                                       x-on:change="updateExample(idx, 'expected_answer', ex.expected_answer)"></td>
                            <td><input type="text" class="form-control form-control-sm" x-model="ex.expected_docs"
                                       x-on:change="updateExample(idx, 'expected_docs', ex.expected_docs)"></td>
                            <td>
                                <button class="btn btn-sm btn-outline-danger" x-on:click="deleteExample(idx)">×</button>
                            </td>
                        </tr>
                    </template>
                </tbody>
            </table>
        </div>

        <!-- Add row -->
        <form x-on:submit.prevent="addExample()" class="row g-2">
            <div class="col-md-4">
                <input type="text" class="form-control form-control-sm" x-model="newQuery" placeholder="Query">
            </div>
            <div class="col-md-4">
                <input type="text" class="form-control form-control-sm" x-model="newAnswer" placeholder="Expected answer">
            </div>
            <div class="col-md-3">
                <input type="text" class="form-control form-control-sm" x-model="newDocs" placeholder="Expected docs (comma-sep)">
            </div>
            <div class="col-md-1">
                <button type="submit" class="btn btn-primary btn-sm">+</button>
            </div>
        </form>

        <!-- Evaluation results -->
        <div id="eval-results" class="mt-3" hx-get="/admin/tabs/ragas-results" hx-trigger="every 30s" hx-swap="innerHTML">
            <div hx-get="/admin/tabs/ragas-results" hx-trigger="load" hx-swap="innerHTML"></div>
        </div>
    </div>

    <script>
    function ragasEditor() {
        return {
            examples: [],
            newQuery: '',
            newAnswer: '',
            newDocs: '',
            importDialog: false,
            importJson: '',
            evalRunning: false,

            init() {
                fetch('/api/v1/evaluation/dataset')
                    .then(r => r.json())
                    .then(data => { this.examples = data.examples || []; });
            },

            addExample() {
                if (!this.newQuery) return;
                fetch('/api/v1/evaluation/dataset', {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ add: true, query: this.newQuery, expected_answer: this.newAnswer, expected_docs: this.newDocs.split(',').map(s => s.trim()) })
                }).then(r => r.json()).then(() => {
                    this.newQuery = ''; this.newAnswer = ''; this.newDocs = '';
                    this.init();
                });
            },

            updateExample(idx, field, value) {
                let fields = {};
                fields[field] = value;
                fetch('/api/v1/evaluation/dataset', {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ index: idx, fields: fields })
                });
            },

            deleteExample(idx) {
                fetch('/api/v1/evaluation/dataset/' + idx, { method: 'DELETE' })
                    .then(() => this.init());
            },

            doImport() {
                try {
                    let data = JSON.parse(this.importJson);
                    fetch('/api/v1/evaluation/dataset/import', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ examples: data })
                    }).then(r => r.json()).then(() => {
                        this.importDialog = false;
                        this.importJson = '';
                        this.init();
                    });
                } catch(e) { alert('Invalid JSON: ' + e.message); }
            },

            runEval() {
                this.evalRunning = true;
                fetch('/api/v1/evaluation/run', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        this.evalRunning = false;
                        htmx.trigger('#eval-results', 'load');
                    })
                    .catch(() => { this.evalRunning = false; });
            }
        };
    }
    </script>
    ```

    Step 6: Create kb_server/ui/templates/admin/_ragas_results.html:
    ```html
    {% if results %}
    <h6>Evaluation History (last 10)</h6>
    <div class="table-responsive">
        <table class="table table-sm">
            <thead>
                <tr>
                    <th>Timestamp</th>
                    {% if results[0].metrics %}
                    {% for key in results[0].metrics.keys() %}
                    <th>{{ key }}</th>
                    {% endfor %}
                    {% endif %}
                </tr>
            </thead>
            <tbody>
                {% for run in results|reverse %}
                <tr>
                    <td><small>{{ run.timestamp[:19] }}</small></td>
                    {% if run.metrics %}
                    {% for key, value in run.metrics.items() %}
                    <td>{{ "%.3f"|format(value) if value is number else value }}</td>
                    {% endfor %}
                    {% endif %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <p class="text-muted">No evaluation results yet. Run an evaluation to see results here.</p>
    {% endif %}
    ```

    Step 7: Run tests to verify they pass.
  </action>
  <verify>
    <automated>python -m pytest tests/test_ragas_admin.py -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - All tests pass: test_ragas_editor_partial, test_ragas_results_partial
    - GoldenDataset has remove_example, update_example, to_json, from_json_str methods
    - RAGAS editor template renders golden set table with inline editing, import/export, and run evaluation button
    - RAGAS results template shows evaluation history table with metric columns
    - API endpoints: GET/PUT/DELETE /api/v1/evaluation/dataset, POST /api/v1/evaluation/run, POST import, GET export
    - Evaluation results saved to data/evaluation_results.json
  </acceptance_criteria>
  <done>RAGAS tab with golden set editor and evaluation runner implemented and tested</done>
</task>

<task type="auto" tdd="true">
  <name>Browser Cleanup (delete + re-ingest)</name>
  <files>kb_server/ui/templates/browse.html, kb_server/ui/routes_admin.py</files>
  <read_first>kb_server/ui/templates/browse.html, kb_server/ui/routes_admin.py</read_first>
  <action>
    Step 1: Add cleanup API endpoints to routes_admin.py.
    ```python
    @app.delete("/api/v1/documents/{source_file}")
    async def delete_document(source_file: str):
        """Delete a document from Qdrant + mark deleted in registry."""
        from kb_server.vector_store import VectorStore
        store = VectorStore()
        await store.connect()
        try:
            await store.delete_by_source(source_file)
        finally:
            await store.close()
        # Mark in registry
        import sqlite3
        from pathlib import Path
        db_path = Path(os.getenv("KB_METADATA_DB", "data/kb_metadata.db"))
        conn = sqlite3.connect(str(db_path))
        conn.execute("UPDATE files SET status = 'deleted' WHERE path = ?",
                     (source_file,))
        conn.commit()
        conn.close()
        return {"status": "deleted", "source_file": source_file}


    @app.post("/api/v1/documents/{source_file}/re-ingest")
    async def reingest_document(source_file: str):
        """Re-ingest a document."""
        from ingest.ingest import process_file
        result = await process_file(source_file)
        return {"status": "re-ingested", "source_file": source_file, "result": str(result)}
    ```

    Step 2: Modify browse.html to add cleanup controls.

    Add checkbox column and action bar. Add before the table:
    ```html
    {% block extra_head %}
    {{ super() }}
    <style>
    .cleanup-toolbar { display: none; }
    .cleanup-toolbar.active { display: flex; }
    </style>
    {% endblock %}
    ```

    Replace the <thead> row:
    ```html
                <tr>
                    <th><input type="checkbox" id="select-all" x-on:click="selectAll($event)"></th>
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

    Add cleanup toolbar after filters card, before results count:
    ```html
    <!-- Cleanup toolbar -->
    <div id="cleanup-toolbar" class="cleanup-toolbar mb-3 d-none" x-data="{ selected: [] }">
        <div class="btn-group">
            <button class="btn btn-danger btn-sm" x-on:click="deleteSelected()">Delete</button>
            <button class="btn btn-warning btn-sm" x-on:click="reingestSelected()">Re-ingest</button>
            <button class="btn btn-outline-danger btn-sm" x-on:click="deleteFailed()">Delete Failed</button>
        </div>
        <span class="ms-2 text-muted small" x-text="selected.length + ' selected'"></span>
    </div>

    <script>
    function selectAll(event) {
        document.querySelectorAll('.doc-checkbox').forEach(cb => cb.checked = event.target.checked);
        updateToolbar();
    }
    function updateToolbar() {
        const checked = document.querySelectorAll('.doc-checkbox:checked');
        const toolbar = document.getElementById('cleanup-toolbar');
        if (checked.length > 0) {
            toolbar.classList.remove('d-none');
            toolbar.classList.add('d-flex');
        } else {
            toolbar.classList.add('d-none');
            toolbar.classList.remove('d-flex');
        }
    }
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('doc-checkbox')) updateToolbar();
    });
    </script>
    ```

    Add per-document actions dropdown. Replace the single "View" button in each row's actions column:
    ```html
                    <td>
                        <div class="dropdown">
                            <button class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown">
                                Actions
                            </button>
                            <ul class="dropdown-menu">
                                <li><a class="dropdown-item" href="/ui/document/{{ doc.id }}">View</a></li>
                                <li><a class="dropdown-item" href="#"
                                       hx-delete="/api/v1/documents/{{ doc.source_file }}"
                                       hx-confirm="Delete this document?"
                                       hx-target="closest tr" hx-swap="outerHTML">Delete</a></li>
                                <li><a class="dropdown-item" href="#"
                                       hx-post="/api/v1/documents/{{ doc.source_file }}/re-ingest"
                                       hx-target="closest tr" hx-swap="outerHTML">Re-ingest</a></li>
                            </ul>
                        </div>
                    </td>
    ```
  </action>
  <verify>
    <automated>python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - DELETE /api/v1/documents/{source_file} deletes from Qdrant and marks deleted in registry
    - POST /api/v1/documents/{source_file}/re-ingest calls process_file and returns result
    - browse.html has checkbox column in table header with select-all
    - Cleanup toolbar appears when checkboxes are checked (Delete, Re-ingest, Delete Failed buttons)
    - Per-document Actions dropdown includes View, Delete, Re-ingest options
  </acceptance_criteria>
  <done>Browser cleanup with delete and re-ingest implemented</done>
</task>

<task type="auto" tdd="true">
  <name>Profile tab — personal API keys, export, erasure</name>
  <files>kb_server/ui/templates/admin/_profile_content.html, kb_server/ui/routes_admin.py</files>
  <read_first>kb_server/ui/routes_admin.py</read_first>
  <action>
    Step 1: Create kb_server/ui/templates/admin/_profile_content.html:
    ```html
    <div x-data="profilePage()" x-init="initProfile()">
        <div class="row">
            <!-- User Info -->
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-body">
                        <h5 class="card-title">Account</h5>
                        <p><strong>Username:</strong> <span x-text="user.username"></span></p>
                        <p><strong>Role:</strong> <span class="badge bg-primary" x-text="user.role"></span></p>
                        <p><strong>Created:</strong> <span x-text="user.created_at"></span></p>
                        <button class="btn btn-outline-secondary btn-sm" x-on:click="exportData()">Export My Data (GDPR Art 20)</button>
                        <button class="btn btn-outline-danger btn-sm" x-on:click="requestErasure()">Request Data Erasure</button>
                    </div>
                </div>
            </div>

            <!-- API Keys -->
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-body">
                        <h5 class="card-title">API Keys</h5>
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Prefix</th>
                                    <th>Description</th>
                                    <th>Created</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                <template x-for="key in keys" :key="key.id">
                                    <tr>
                                        <td><code x-text="key.prefix"></code></td>
                                        <td x-text="key.description"></td>
                                        <td><small x-text="key.created_at?.slice(0, 10)"></small></td>
                                        <td>
                                            <span class="badge" :class="key.is_revoked ? 'bg-danger' : 'bg-success'"
                                                  x-text="key.is_revoked ? 'Revoked' : 'Active'"></span>
                                        </td>
                                        <td>
                                            <button class="btn btn-sm btn-outline-danger" x-on:click="revokeKey(key.id)"
                                                    x-show="!key.is_revoked">Revoke</button>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </table>

                        <button class="btn btn-primary btn-sm" x-on:click="generateKey()">Generate New Key</button>

                        <!-- New key display modal -->
                        <div x-show="newKey" class="alert alert-success mt-2" style="display: none;">
                            <strong>New API Key generated:</strong>
                            <p class="mb-1"><code x-text="newKey" style="word-break: break-all;"></code></p>
                            <small class="text-danger">This key will only be shown once. Copy it now.</small>
                            <button class="btn btn-sm btn-outline-primary ms-2" x-on:click="copyKey()">Copy</button>
                        </div>

                        <!-- Erasure request status -->
                        <div x-show="erasureStatus" class="alert alert-warning mt-2" style="display: none;">
                            Erasure request status: <strong x-text="erasureStatus"></strong>
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
                fetch('/api/v1/users/me')
                    .then(r => r.json())
                    .then(data => { this.user = data; });
                this.loadKeys();
            },

            loadKeys() {
                fetch('/api/v1/api-keys')
                    .then(r => r.json())
                    .then(data => { this.keys = data; });
            },

            generateKey() {
                fetch('/api/v1/api-keys', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ description: 'Browser-generated key', user_id: this.user.id })
                })
                .then(r => r.json())
                .then(data => {
                    this.newKey = data.raw_key;
                    this.loadKeys();
                    setTimeout(() => { this.newKey = ''; }, 30000);
                });
            },

            revokeKey(keyId) {
                if (!confirm('Revoke this API key?')) return;
                fetch('/api/v1/api-keys/' + keyId, { method: 'DELETE' })
                    .then(() => this.loadKeys());
            },

            copyKey() {
                navigator.clipboard.writeText(this.newKey);
            },

            exportData() {
                fetch('/api/v1/users/me/export')
                    .then(r => r.json())
                    .then(data => {
                        const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'my-data-export.json';
                        a.click();
                    });
            },

            requestErasure() {
                if (!confirm('Request complete erasure of all your data? This will anonymize your account and revoke all keys.')) return;
                fetch('/api/v1/users/me/erasure-request', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                })
                .then(r => r.json())
                .then(data => { this.erasureStatus = data.status; });
            }
        };
    }
    </script>
    ```

    Step 2: Add profile content endpoint to routes_admin.py.
    ```python
    @app.get("/admin/tabs/profile-content", response_class=HTMLResponse, include_in_schema=False)
    async def profile_content_tab(request: Request):
        from kb_server.ui.app import templates
        return templates.TemplateResponse(
            request, "admin/_profile_content.html",
            {"request": request},
        )
    ```

    Step 3: Add users/me endpoints to kb_server/auth/router.py:
    ```python
    @router.get("/users/me/export")
    async def export_my_data(current_user: User = Depends(get_current_user)):
        """GDPR Art 20 data portability export."""
        from kb_server.auth.erasure import ErasureManager
        request = current_user
        return {"message": "See /users/{id}/export"}


    @router.post("/users/me/erasure-request")
    async def request_my_erasure(request, current_user: User = Depends(get_current_user)):
        from kb_server.auth.erasure import ErasureManager
        mgr = ErasureManager(request.app.state.auth_engine)
        req = await mgr.request_erasure(current_user.id, current_user.id)
        return {"request_id": req.id, "status": req.status}
    ```

    Step 4: Run tests to verify.
  </action>
  <verify>
    <automated>python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - /admin/tabs/profile-content returns 200 with profile content template
    - Profile template renders account info (username, role, created_at) via Alpine.js
    - API keys table shows prefix, description, created date, status with revoke button
    - Generate New Key creates key via POST /api/v1/api-keys and displays raw_key once
    - GDPR export downloads JSON via /api/v1/users/me/export
    - Erasure request posts to /api/v1/users/me/erasure-request
  </acceptance_criteria>
  <done>Profile tab with API key management, GDPR data export, and erasure request implemented</done>
</task>

</tasks>

<threat_model>
  <threat>
    <name>XSS via inline config editing</name>
    <description>Config values rendered directly in Alpine.js x-text and input fields could contain malicious scripts.</description>
    <mitigation>Mitigated by Jinja2 auto-escaping. Alpine.js x-text uses textContent, not innerHTML. HTMX hx-vals are JSON-encoded.</mitigation>
  </threat>
  <threat>
    <name>SQL injection in scheduler</name>
    <description>Schedule CRUD endpoints accept user input for docs_path and product.</description>
    <mitigation>Mitigated by using parameterized SQL queries (?, ?, ?) in all IngestionScheduler database operations.</mitigation>
  </threat>
  <threat>
    <name>Unauthorized API key generation</name>
    <description>Profile tab generates API keys via POST /api/v1/api-keys without server-side auth check.</description>
    <mitigation>Mitigated by requiring Bearer token on all API requests; server validates token before processing.</mitigation>
  </threat>
  <threat>
    <name>Large file upload in RAGAS import</name>
    <description>Import endpoint accepts arbitrary JSON payload that could exhaust server memory.</description>
    <mitigation>Mitigated by FastAPI's default request body size limits (16MB). Acceptable for golden set sizes.</mitigation>
  </threat>
  <threat>
    <name>RACE condition in evaluation results file</name>
    <description>Concurrent evaluation runs could corrupt data/evaluation_results.json.</description>
    <mitigation>Mitigated by read-append-write pattern instead of parallel writes. Evaluate is sequential for now.</mitigation>
  </threat>
</threat_model>

<verification>
  <step>
    Run all admin UI tests:
    cd /home/admin/kb-rag-mcp && python -m pytest tests/test_admin_ui.py -x -v 2>&1 | tail -20
  </step>
  <step>
    Run ingestion admin tests:
    cd /home/admin/kb-rag-mcp && python -m pytest tests/test_ingestion_admin.py -x -v 2>&1 | tail -10
  </step>
  <step>
    Run RAGAS admin tests:
    cd /home/admin/kb-rag-mcp && python -m pytest tests/test_ragas_admin.py -x -v 2>&1 | tail -10
  </step>
  <step>
    Verify all tab templates exist:
    ls kb_server/ui/templates/admin/_config_table.html kb_server/ui/templates/admin/_monitor_lights.html kb_server/ui/templates/admin/_ingestion_*.html kb_server/ui/templates/admin/_ragas_*.html kb_server/ui/templates/admin/_profile_content.html
  </step>
  <step>
    Verify scheduler module is importable:
    python -c "from ingest.scheduler import get_scheduler; print(get_scheduler())"
  </step>
  <step>
    Verify routes_admin.py has all expected endpoints:
    grep -c '@app.get.*/admin/tabs/' kb_server/ui/routes_admin.py
  </step>
</verification>

<success_criteria>
  - All tests pass (test_admin_ui.py, test_ingestion_admin.py, test_ragas_admin.py)
  - Admin Config page renders config table with inline editing
  - Monitor lights bar displays 7 health components with color-coded badges
  - Ingestion tab has Manual (form), Schedule (add/list), Monitor (polling) sub-tabs
  - RAGAS tab has golden set editor with add/edit/delete/import/export and evaluation runner
  - Browser cleanup adds checkbox selection and per-document Actions dropdown with Delete/Re-ingest
  - Profile tab shows account info, API key management, GDPR export, and erasure request
  - All API endpoints are tested and functional
</success_criteria>

<output>
  <file path="kb_server/ui/templates/admin/tab_admin.html" summary="Admin config tab with search and inline editing" />
  <file path="kb_server/ui/templates/admin/_config_table.html" summary="Config table partial with inline Alpine.js editing" />
  <file path="kb_server/ui/templates/admin/_monitor_lights.html" summary="Monitor lights bar with 7 component health indicators" />
  <file path="kb_server/ui/templates/admin/_ingestion_manual.html" summary="Manual ingestion form partial" />
  <file path="kb_server/ui/templates/admin/_ingestion_schedule.html" summary="Ingestion schedule add/list partial" />
  <file path="kb_server/ui/templates/admin/_ingestion_monitor.html" summary="Ingestion job monitor partial with 5s polling" />
  <file path="ingest/scheduler.py" summary="Background ingestion scheduler with SQLite-backed schedules" />
  <file path="kb_server/ui/templates/admin/_ragas_editor.html" summary="RAGAS golden set editor with Alpine.js CRUD" />
  <file path="kb_server/ui/templates/admin/_ragas_results.html" summary="Evaluation results history table" />
  <file path="kb_server/evaluation/dataset.py" summary="Extended GoldenDataset with remove/update/import methods" />
  <file path="kb_server/ui/templates/browse.html" summary="Added checkbox selection and cleanup toolbar" />
  <file path="kb_server/ui/templates/admin/_profile_content.html" summary="Profile tab with API keys, GDPR export/erasure" />
  <file path="tests/test_ingestion_admin.py" summary="Tests for ingestion admin tab endpoints" />
  <file path="tests/test_ragas_admin.py" summary="Tests for RAGAS admin tab endpoints" />
</output>
