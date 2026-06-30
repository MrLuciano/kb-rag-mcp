# 28c-fixes-02 Summary: Monitor Lights, Config Editor, Partials, Route Ordering

## One-liner
Completed monitor lights (7 components with latency/details/ARIA), config inline editor (Reset All, HTMX PUT save, Group badges), 5 new partials for ingestion/RAGAS sub-tabs, responsive sidebar (280px with icon-only/hamburger), and fixed route ordering so specific `/tabs/` paths resolve before generic `{tab_name}`.

## Tasks

- **Task 1** (auto, TDD): Complete monitor lights bar — added LLM as 7th component, latency display (ms), click-to-expand per component, aria-label on status dots, warning/degraded state (bg-warning)
- **Task 2** (auto, TDD): Improve config inline editor — Reset All button with hx-confirm, Group column badges, HTMX PUT save replacing fetch(), aria-live assertive for save errors, search placeholder "Search config keys..."
- **Task 3** (auto, TDD): Create 5 missing partials (`_ingestion_manual`, `_ingestion_schedule`, `_ingestion_monitor`, `_ragas_editor`, `_ragas_results`), update parent tabs with sub-tab nav (Manual/Schedule/Monitor and Editor/Results), responsive sidebar (280px, icon-only 60px at md, hamburger at sm), sidebar ARIA roles, profile content copy/badge fixes, emoji icons on nav
- **Task 4** (auto, TDD): Fix route ordering — registered specific `/tabs/` paths (documents-content, monitor-lights, config-table, profile-content, ingestion-*, ragas-*) before generic `/tabs/{tab_name}` so they resolve correctly

## Verification
- Admin UI tests: all Plan 02 tests pass (monitor, config, partials, sidebar, profile, route)
- `curl /admin/tabs/documents-content` returns document table HTML (not "Unknown tab")
- `curl /admin/tabs/monitor-lights` returns monitor lights HTML
- All 5 new partials render without Jinja2 syntax errors

## Commits
1. `5c17da2` — feat(admin): Task 1 - complete monitor lights bar
2. `9618f6d` — feat(admin): Task 2 - improve config inline editor
3. `5b30411` — feat: Plan 02 Task 3-4 — partials refactor, route reordering, 5 new partial routes
