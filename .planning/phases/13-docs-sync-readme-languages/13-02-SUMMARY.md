---
phase: 13-docs-sync-readme-languages
plan: 02
subsystem: documentation
tags: [readme, v1.3, advanced-sections, health, mcp-tools, architecture, development, monitoring, operations, license]
dependency_graph:
  requires: [13-01]
  provides: [refreshed-readme-advanced]
  affects: [README.md]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - README.md
decisions:
  - "Updated health server path from server.health_server to kb_server.health_server"
  - "Added kb-rag check health CLI alternative to health check documentation"
  - "Updated Prometheus metrics count from 23 to 28 to match observability/metrics.py"
  - "Replaced license placeholder with full MIT License text"
  - "Removed FASE completion report references from Documentation section"
metrics:
  duration_seconds: 1180
  tasks_completed: 3
  files_modified: 1
  commits: 3
  completed_date: "2026-05-25T22:50:30Z"
---

# Phase 13 Plan 02: README.md Advanced Sections Refresh Summary

**One-liner:** Refreshed README.md advanced sections (Health Checks through License/Contributing) with kb_server paths, vendor/subsystem/version parameters, 28 Prometheus metrics, MIT license, and current audit commands.

## Objective

Refresh the bottom half of README.md (Health Checks through License/Contributing) — sections that detail operations, tools, architecture monitoring, and development workflows.

## What Was Done

### Task 1: Refresh Health Checks, Service Management, and MCP Tools sections

**Commit:** `f7a6994`

Updated lines 621-833 of README.md:

1. **Health Checks section:**
   - Updated manual health server command from `python3 -m server.health_server` → `python -m kb_server.health_server`
   - Added CLI alternative: `kb-rag check health`
   - Added note about cross-encoder lazy loading in component checks table

2. **Service Management section:**
   - Added `kb-rag-watcher` (file watcher) to Individual Services list
   - Removed "(when implemented)" qualifier from scheduler service

3. **MCP Tools section:**
   - Added `vendor` parameter to `search_kb` tool
   - Added `subsystem` parameter to `search_kb` tool
   - Updated `search_kb` return fields to include `vendor`, `subsystem` (in addition to existing `version`)
   - Added `vendor`, `subsystem` parameters to `list_documents` tool

### Task 2: Refresh Architecture, Development, Documentation, Monitoring, Operations, Troubleshooting, License, and Contributing

**Commit:** `59d801f`

Updated lines 848-1349 of README.md:

1. **Architecture section:**
   - Updated ASCII diagram: `server/server.py` → `kb_server/server.py`
   - Removed FASE labels from all components (FASE 2, FASE 3, FASE 4, FASE 5)
   - Added "Auto-classification: Vendor, subsystem, version inference"
   - Added "Cross-encoder reranker: Lazy-loaded on first reranking query (~10s faster startup)"

2. **Development section:**
   - Updated test coverage paths: `--cov=ingest --cov=server` → `--cov=kb_server --cov=ingest`
   - Added coverage enforcement command: `--cov-branch --cov-fail-under=90`
   - Added test baseline note: "585 core tests"
   - Updated code quality paths: `black ingest/ server/` → `black kb_server/ ingest/`
   - Added logging audit command: `python scripts/logging-audit.py`
   - Added English audit command: `python scripts/docstring-audit.py --check-inline`

3. **Documentation section:**
   - Removed all FASE completion report references (FASE1 through FASE12)
   - Removed stale INSTRUCTIONS.md and PLAN.md references
   - Added missing doc links: ARCHITECTURE.md, OPERATIONS.md, INDEX.md, REFERENCE.md, KUBERNETES.md
   - Removed "(FASE 12)" label from SEARCH_QUALITY.md

4. **Monitoring section:**
   - Updated metric count: 23 → 28
   - Completely refreshed metric list to match current `observability/metrics.py`:
     - Job Management: 4 metrics (was 5)
     - File Processing: 3 metrics (was 3)
     - Worker Pool: 6 metrics (NEW category)
     - API Requests: 2 metrics (NEW category)
     - Cache Performance: 5 metrics (was 4)
     - Batch Processing: 8 metrics (was 8, but updated names)
   - Removed conceptual "System Health" metrics that don't exist in code

5. **Operations section:**
   - No changes needed (already accurate)

6. **Troubleshooting section:**
   - Updated "No search results" fix to include CLI alternative: `kb-rag status` or `python ingest/ingest.py --status`

7. **License section:**
   - Replaced `[Your License Here]` placeholder with full MIT License text
   - Copyright year: 2026
   - Copyright holder: "KB-RAG MCP Server Contributors"

8. **Contributing section:**
   - Verified CONTRIBUTING.md exists (no changes needed)

### Task 3: Final polish pass — links, anchor tags, version, and consistency

**Commit:** `f2815d5`

Performed final end-to-end verification and fixes:

1. **Version consistency:**
   - Updated example version in Operations section: `sudo ./deployment/scripts/update.sh v0.9.0` → `v1.3`
   - Verified no stale v0.9 or v1.0.0 references remain in English section

2. **FASE label removal:**
   - Removed "FASE 8" label from Batch Processing section
   - Verified 0 FASE labels remain in English section (lines 1-1352)

3. **Link validation:**
   - Verified all 11 docs/ links resolve to existing files
   - All links valid: ARCHITECTURE, AUTO_INGESTION, INDEX, KUBERNETES, METADATA_OVERRIDES, OPERATIONS, REFERENCE, SEARCH_QUALITY, TESTING, TROUBLESHOOTING, VERSION_FILTERING

4. **Markdown formatting:**
   - Verified code fences balanced (120 total, even number)
   - No unclosed blocks detected

5. **Portuguese section:**
   - Left unchanged per plan requirements (lines 1353-1729)

## Success Criteria

✅ **All criteria met:**

- [x] All MCP tools documented with vendor, subsystem, version parameters
- [x] Architecture diagram uses kb_server/ paths
- [x] Development section uses flake8, black, isort, mypy with correct flags
- [x] Monitoring section matches current 28 metrics (updated from 23)
- [x] License section has MIT text instead of placeholder
- [x] All 11 docs/FILENAME.md links verified valid
- [x] No `server/` paths, FASE labels, or (NEW) badges remain in English sections

## Verification Results

### Automated Checks (from plan)

```
vendor mentions: 6 ✅
subsystem mentions: 5 ✅
(NEW in FASE) labels: 0 ✅
kb_server references: 13 ✅
Old health server path: 0 ✅
flake8 references: 1 ✅
cov=kb_server: 2 ✅
cross-encoder: 1 ✅
MIT License: 1 ✅
logging-audit: 1 ✅
docstring-audit: 1 ✅
Old cov=server paths: 0 ✅
License placeholder: 0 ✅

Version consistency:
  v1.3 mentions: 3 ✅
  Stale versions (v0.9, v1.0.0): 0 ✅

FASE labels in English: 0 ✅

Docs links validated: 11/11 valid ✅
  - ARCHITECTURE.md
  - AUTO_INGESTION.md
  - INDEX.md
  - KUBERNETES.md
  - METADATA_OVERRIDES.md
  - OPERATIONS.md
  - REFERENCE.md
  - SEARCH_QUALITY.md
  - TESTING.md
  - TROUBLESHOOTING.md
  - VERSION_FILTERING.md

Markdown formatting:
  Total code fences: 120 (balanced) ✅
```

### Manual Verification

- [x] Health server path updated to kb_server.health_server
- [x] CLI health check alternative added (kb-rag check health)
- [x] Cross-encoder lazy loading note added
- [x] File watcher service added to service list
- [x] MCP tools include vendor, subsystem parameters
- [x] Architecture diagram shows kb_server/server.py
- [x] All FASE labels removed from components
- [x] Auto-classification and cross-encoder documented
- [x] Development commands use kb_server paths
- [x] Audit commands added (logging-audit, docstring-audit)
- [x] Prometheus metrics count accurate (28)
- [x] License has full MIT text
- [x] All version references are v1.3
- [x] Portuguese section unchanged

## Deviations from Plan

None — plan executed exactly as written.

**Threat Model Compliance:**

All mitigations from `<threat_model>` applied:

- T-13-03: Health endpoint paths verified against `kb_server/health_server.py` ✅
- T-13-04: Code quality tool flags verified against `.flake8`, `pyproject.toml` ✅
- T-13-05: Prometheus metric names verified against `observability/metrics.py` ✅
- T-13-SC: No package installs in this plan (accepted) ✅

## Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| README.md | +97/-49 | Refreshed Health Checks through Contributing sections; updated paths, tools, metrics, license |

## Commits

| Commit | Message | Files |
|--------|---------|-------|
| `f7a6994` | docs(13-02): refresh Health Checks, Service Management, and MCP Tools sections | README.md |
| `59d801f` | docs(13-02): refresh Architecture through Contributing sections | README.md |
| `f2815d5` | docs(13-02): final polish pass - version consistency and FASE removal | README.md |

## Impact

### User-Facing Changes

- Operators see accurate health check commands (kb-rag check health CLI)
- Developers see correct kb_server paths in all examples
- MCP tool users see vendor, subsystem, version parameters documented
- All users see accurate Prometheus metrics (28, not 23)
- License is explicit (MIT) instead of placeholder

### Documentation Changes

- README.md English section fully refreshed (lines 621-1349)
- All advanced sections reflect v1.3 state
- No stale FASE labels or server/ paths remain
- All docs/ links verified valid

### Technical Debt

None introduced. Removed stale labels, paths, and placeholders.

## Known Stubs

None — all documented features are fully implemented and tested.

## Self-Check

✅ **PASSED**

**Files created/modified:**
```
✅ FOUND: README.md (modified with 3 commits)
✅ FOUND: .planning/phases/13-docs-sync-readme-languages/13-02-SUMMARY.md (this file)
```

**Commits:**
```
✅ FOUND: f7a6994 (docs(13-02): refresh Health Checks, Service Management, and MCP Tools sections)
✅ FOUND: 59d801f (docs(13-02): refresh Architecture through Contributing sections)
✅ FOUND: f2815d5 (docs(13-02): final polish pass - version consistency and FASE removal)
```

**Content verification:**
```
✅ Health server path: kb_server.health_server
✅ CLI health check: kb-rag check health
✅ Cross-encoder: lazy loading noted
✅ File watcher: in service list
✅ MCP tools: vendor, subsystem parameters added
✅ Architecture: kb_server/server.py path
✅ Components: no FASE labels
✅ Development: kb_server coverage paths
✅ Audit commands: logging-audit, docstring-audit
✅ Prometheus: 28 metrics documented
✅ License: MIT full text
✅ Version: v1.3 throughout
✅ Links: 11/11 valid
✅ Portuguese: unchanged
```

## Next Steps

- Plan 13-03: Sync README.pt-BR.md with English structure and translate new sections
- Plan 13-04: Create README.es.md (Spanish translation)
- Plan 13-05: Update stale docs (AUTO_INGESTION, TROUBLESHOOTING, TESTING, KUBERNETES)
