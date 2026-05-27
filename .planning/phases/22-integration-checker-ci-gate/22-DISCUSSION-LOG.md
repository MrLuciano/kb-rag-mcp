# Phase 22: Integration Checker CI Gate - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 22-integration-checker-ci-gate
**Areas discussed:** Gap scope, Implementation language, CI integration point, Fail behavior & reporting

---

## Gap Scope

**Question:** What should the checker validate?

| Option | Description | Selected |
|--------|-------------|----------|
| VERIFICATION.md + requirements trace (Recommended) | Check VERIFICATION.md presence + REQUIREMENTS.md traceability | ✓ |
| Full doc-implementation sync | All above + SUMMARY.md references validated against disk | |
| VERIFICATION.md only (keep existing) | Keep existing bash script behavior | |

**User's choice:** VERIFICATION.md + requirements trace

**Question:** Validate referenced files in SUMMARY.md?

| Option | Description | Selected |
|--------|-------------|----------|
| Validate referenced files exist (Recommended) | Check key-files.modified exist on disk | ✓ |
| Structure-only check | Only check VERIFICATION.md presence and REQUIREMENTS traceability | |
| Also check codebase docs vs reality | Check STRUCTURE.md vs actual code layout | |

**User's choice:** Validate referenced files exist

---

## Implementation Language

**Question:** What language/framework for the checker?

| Option | Description | Selected |
|--------|-------------|----------|
| Python script in scripts/ (Recommended) | Python-based checker in scripts/ directory | ✓ |
| Extended bash script | Extend existing check-verification-gaps.sh | |
| CLI subcommand (kb-ingest check) | New Typer subcommand | |

**User's choice:** Python script in scripts/

**Question:** Script naming?

| Option | Description | Selected |
|--------|-------------|----------|
| check-integration-gaps.py (Recommended) | Follows existing script naming patterns | ✓ |
| integration-checker.py | Shorter, aligned with phase name | |
| You decide | Agent discretion | |

**User's choice:** check-integration-gaps.py

---

## CI Integration Point

**Question:** How to integrate into CI?

| Option | Description | Selected |
|--------|-------------|----------|
| New CI job (depends on test) (Recommended) | Independent integration-check job | ✓ |
| Step in existing test job | Additional step in test job | |
| PR-to-master only (like coverage) | Limited to PR to master | |

**User's choice:** New CI job (depends on test)

**Question:** CI trigger?

| Option | Description | Selected |
|--------|-------------|----------|
| Every push and PR (Recommended) | Runs on all pushes and PRs | ✓ |
| PR to master only | Like coverage enforcement and logging audit | |
| You decide | Agent discretion | |

**User's choice:** Every push and PR

---

## Fail Behavior & Reporting

**Question:** What causes CI to fail?

| Option | Description | Selected |
|--------|-------------|----------|
| All gaps fail CI (Recommended) | Any unresolved gap causes failure | ✓ |
| Structural gaps fail, file refs warn | VERIFICATION.md + REQUIREMENTS fail, SUMMARY.md refs warn | |
| Same as existing bash script | Only missing VERIFICATION.md fails | |

**User's choice:** All gaps fail CI

**Question:** Reporting format?

| Option | Description | Selected |
|--------|-------------|----------|
| Rich stdout + JSON summary (Recommended) | Human-readable table + machine-parseable JSON | ✓ |
| Plain text only | Minimal text output | |
| stdout + GHA annotations | GitHub Actions workflow-commands | |

**User's choice:** Rich stdout + JSON summary

---

## Decisions Summary

| ID | Decision |
|----|----------|
| D-01 | Check VERIFICATION.md presence per phase |
| D-02 | Check REQUIREMENTS.md traceability |
| D-03 | Validate SUMMARY.md key-files.modified references exist on disk |
| D-04 | Python script in scripts/ |
| D-05 | Named check-integration-gaps.py |
| D-06 | New CI job with needs: test |
| D-07 | Runs on every push and PR |
| D-08 | All gap types hard-fail CI |
| D-09 | Rich stdout + JSON summary output |
