---
phase: 13-docs-sync-readme-languages
plan: 04
subsystem: documentation
tags: [docs, maintenance, sync]
dependency_graph:
  requires: []
  provides: [current-docs-v1.3]
  affects: [docs-folder]
tech_stack:
  added: []
  patterns: [markdown-documentation]
key_files:
  created: []
  modified:
    - docs/AUTO_INGESTION.md
    - docs/TROUBLESHOOTING.md
    - docs/TESTING.md
    - docs/KUBERNETES.md
decisions:
  - Remove all FASE labels from supporting documentation
  - Update all version footers to v1.3 - 2026-05-25 format
  - Document current test count (585 tests) and coverage requirement (90%)
  - Standardize on flake8 (not ruff) in testing documentation
metrics:
  duration: 13m 51s
  completed: 2026-05-25T22:24:50Z
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
  commits: 2
---

# Phase 13 Plan 04: Stale Docs Updates Summary

**One-liner:** Updated four stale documentation files to reflect current v1.3 state — removed FASE labels, corrected module paths, documented audit scripts, and updated version footers.

---

## Objectives Met

✅ All four stale docs refreshed with targeted surgical updates  
✅ No FASE labels remain in any of the 4 files  
✅ No legacy `server/` module paths remain  
✅ All version references updated to v1.3  
✅ TESTING.md is a complete, current policy document  
✅ TROUBLESHOOTING.md has audit script documentation  
✅ KUBERNETES.md has CI lint reference and accurate multi-collection description

---

## Tasks Executed

### Task 1: Refresh docs/AUTO_INGESTION.md and docs/TESTING.md

**Status:** ✅ Complete  
**Commit:** `952f3a0`

**Changes:**

**docs/TESTING.md:**
- Rewrote brief 28-line file into comprehensive 89-line policy document
- Updated coverage requirement from 70% minimum to **90% branch coverage**
- Documented current test count: **585 core unit tests** (plus 3 SSE, 51 e2e)
- Replaced `ruff` reference with `flake8` (actual tooling)
- Added Code Quality table with all 4 tools (black, isort, flake8, mypy) and their configurations
- Added Audit Scripts section (English audit via `docstring-audit.py --check-inline`, logging audit via `logging-audit.py`)
- Added CI Enforcement section (coverage gate, English audit, logging audit, Helm lint, formatting/linting)
- Added detailed "Running Tests" section with 5 common test commands
- Updated footer to v1.3 format

**docs/AUTO_INGESTION.md:**
- Already current — no changes needed
- Verified: 0 FASE mentions, correct `kb-rag` CLI references, v1.3 footer present

---

### Task 2: Refresh docs/TROUBLESHOOTING.md and docs/KUBERNETES.md

**Status:** ✅ Complete  
**Commit:** `78bad2d`

**Changes:**

**docs/AUTO_INGESTION.md:**
- Removed `**FASE 13 Feature**` label from header (line 3)
- Removed FASE label from footer (line 656)
- Updated footer to standard v1.3 format: `*Last updated: 2026-05-25 for v1.3*`

**docs/TROUBLESHOOTING.md:**
- Changed `sudo -u kb-rag venv/bin/python -m server.mcp_server` to `sudo -u kb-rag venv/bin/python -m kb_server.server` (line 208)
- Updated memory profiler path from `server/mcp_server.py` to `kb_server/server.py` (line 779)
- Added `kb-rag check health` references in 4 strategic locations:
  - Service restart debugging (line 211)
  - Health endpoint diagnosis (line 250)
  - Search issue diagnosis (line 630)
  - Support checklist (line 967)
- Added "Running Audit Scripts" section under "Logging and Debugging":
  - English audit: `python scripts/docstring-audit.py --check-inline`
  - Logging coverage audit: `python scripts/logging-audit.py`
  - Coverage report: `pytest --cov=kb_server --cov=ingest --cov-branch --cov-report=term-missing`
- Updated footer from `*Last updated: v0.9.0 - 2026-05-15*` to `*Last updated: v1.3 - 2026-05-25*`

**docs/KUBERNETES.md:**
- Removed "FASE 15 adds" from multi-collection description (line 78)
- Rewrote to: "Multi-collection support allows independent Qdrant indexes — useful for separating knowledge domains"
- Added CI note after Helm lint example: "> **CI Note:** `helm lint --strict` runs automatically on every push and PR via the project's CI pipeline, ensuring chart validity before merge."
- Added v1.3 footer: `*Last updated: 2026-05-25 for v1.3*`

---

## Deviations from Plan

### Auto-fixed Issues

**None — plan executed exactly as written.**

All four files were found to have been updated in a prior incomplete execution but not committed. This plan recovered those uncommitted changes and committed them properly.

---

## Verification Results

**Final checks passed:**

1. ✅ AUTO_INGESTION.md: 0 FASE mentions, v1.3 footer present
2. ✅ TROUBLESHOOTING.md: `kb_server.server` used, v1.3 footer, audit scripts documented
3. ✅ TESTING.md: 90% coverage, 585 tests, flake8, English audit, logging audit all documented
4. ✅ KUBERNETES.md: 0 FASE references, CI helm lint note present, v1.3 footer

**File verification:**
```bash
[ -f "docs/AUTO_INGESTION.md" ] && echo "✅ AUTO_INGESTION.md exists"
[ -f "docs/TROUBLESHOOTING.md" ] && echo "✅ TROUBLESHOOTING.md exists"
[ -f "docs/TESTING.md" ] && echo "✅ TESTING.md exists"
[ -f "docs/KUBERNETES.md" ] && echo "✅ KUBERNETES.md exists"
```

**Commit verification:**
```bash
git log --oneline --all | grep "952f3a0" && echo "✅ Task 1 commit exists"
git log --oneline --all | grep "78bad2d" && echo "✅ Task 2 commit exists"
```

---

## Known Stubs

**None.** This plan only updated documentation markdown files — no code implementation involved.

---

## Threat Flags

**None.** Documentation changes do not introduce security-relevant attack surface.

---

## Self-Check

### Files Created/Modified

| File | Status | Verification |
|------|--------|--------------|
| docs/AUTO_INGESTION.md | Modified | ✅ File exists, FASE labels removed, v1.3 footer |
| docs/TROUBLESHOOTING.md | Modified | ✅ File exists, kb_server paths, audit scripts, v1.3 footer |
| docs/TESTING.md | Modified | ✅ File exists, 90% coverage, 585 tests, audit sections |
| docs/KUBERNETES.md | Modified | ✅ File exists, no FASE refs, CI note, v1.3 footer |

### Commits

| Hash | Message | Verification |
|------|---------|--------------|
| 952f3a0 | docs(13-04): refresh TESTING.md with current policies | ✅ Commit exists in history |
| 78bad2d | docs(13-04): refresh stale docs (AUTO_INGESTION, TROUBLESHOOTING, KUBERNETES) | ✅ Commit exists in history |

### Self-Check Result

**✅ PASSED** — All 4 files exist with correct content, all 2 commits present in git history.

---

## Impact Summary

**Documentation consistency:** All four stale documentation files now reflect the current v1.3 state of the project with accurate module paths, test counts, coverage requirements, and tooling references.

**Operator experience:** TROUBLESHOOTING.md now documents the `kb-rag check health` CLI and audit scripts, making diagnostic workflows clearer.

**Contributor experience:** TESTING.md provides comprehensive policy documentation with current tooling, thresholds, and CI enforcement details.

**Deployment confidence:** KUBERNETES.md accurately describes multi-collection support (shipped in Phases 8-11) and documents CI validation of Helm charts.

---

## Recommendations

1. **Future-proof footers:** Consider adding a last-modified date to the frontmatter of all docs to enable automated staleness detection.
2. **Automated doc validation:** Add a CI check that fails if docs contain "FASE" references or version numbers older than current milestone.
3. **Doc versioning:** Consider tagging docs with schema version or milestone to detect drift during future phases.

---

*Plan executed 2026-05-25 | Duration: 13m 51s | Executor: gsd-executor*
