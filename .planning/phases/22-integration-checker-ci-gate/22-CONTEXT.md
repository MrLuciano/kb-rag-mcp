# Phase 22: Integration Checker CI Gate - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire an integration checker script into the CI pipeline (after tests) to catch integration gaps before they
reach master. The script validates cross-referencing between documentation, requirement traceability, and
plan implementation — extending the existing VERIFICATION.md presence check into a comprehensive gap
detection system.

**Requirements (from REQUIREMENTS.md):**
- CICHECK-01: Runs in CI after test execution
- CICHECK-02: Validates no integration gaps exist (docs <-> code, plans <-> implementation)
- CICHECK-03: CI fails if checker finds unresolved gaps
- CICHECK-04: Results reported in CI output for debugging

</domain>

<decisions>
## Implementation Decisions

### Gap Scope
- **D-01:** Check VERIFICATION.md presence per phase — all planned phases must have a VERIFICATION.md
- **D-02:** Check REQUIREMENTS.md traceability — every REQ-ID must map to a plan phase and a verification
- **D-03:** Validate SUMMARY.md key-files.modified references — every file path listed as modified in a
  plan SUMMARY.md must exist on disk

### Implementation Language
- **D-04:** New Python script in `scripts/` directory (follows pattern of `scripts/logging-audit.py`)
- **D-05:** Named `scripts/check-integration-gaps.py`

### CI Integration Point
- **D-06:** New independent CI job called `integration-check` that depends on the `test` job completing first
- **D-07:** Runs on every push and every PR (not limited to PR-to-master)

### Fail Behavior & Reporting
- **D-08:** All gap types are hard failures — any unresolved gap causes CI to fail (no thresholds)
- **D-09:** Output is both human-readable (Rich-formatted summary table in stdout) and
  machine-parseable (JSON summary file written alongside)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CI Pipeline
- `.github/workflows/ci.yml` — CI workflow to add the new integration-check job to

### Existing Tooling (Patterns to Follow)
- `scripts/check-verification-gaps.sh` — existing bash-based VERIFICATION.md gap checker (Phase 19)
- `scripts/logging-audit.py` — existing Python audit script pattern (argparse, Rich formatting, exit codes)

### Data Sources
- `.planning/REQUIREMENTS.md` — REQ-ID definitions; traceability source for D-02
- `.planning/phases/*/SUMMARY.md` — parsed for key-files.modified references (D-03)
- `.planning/phases/*/VERIFICATION.md` — presence check target (D-01)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/check-verification-gaps.sh` (203 lines) — VERIFICATION.md gap detection logic that can be wrapped/superseded
- `scripts/logging-audit.py` (298 lines) — Python audit script with argparse, Rich table output, exit code handling
- `.github/workflows/ci.yml` — CI pipeline with jobs for tests, coverage, logging-audit, english-audit, helm-lint

### Established Patterns
- Python scripts in `scripts/` for CI tooling (logging-audit.py, check-verification-gaps.sh)
- Separate CI jobs for independent checks (test, coverage, audit, helm)
- Fail-fast with non-zero exit codes
- Job names use kebab-case in CI (`logging-audit`, `english-audit`, `coverage`)

### Integration Points
- `.github/workflows/ci.yml` — add `integration-check` job with `needs: test`, after the `logging-audit` block
- YAML frontmatter of PLAN.md/SUMMARY.md files — parsed via Python yaml or regex
- REQUIREMENTS.md section headers — regex for REQ-ID patterns

</code_context>

<specifics>
No specific requirements — implementation follows existing patterns for CI tooling.
</specifics>

<deferred>
None — discussion stayed within phase scope.
</deferred>

---

*Phase: 22-integration-checker-ci-gate*
*Context gathered: 2026-05-27*
