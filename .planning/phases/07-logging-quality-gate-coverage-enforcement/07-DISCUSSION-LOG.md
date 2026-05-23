# Phase 7: Logging, Quality Gate & Coverage Enforcement - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-23
**Phase:** 7-Logging, Quality Gate & Coverage Enforcement
**Areas discussed:** Coverage scope, Uncovered margin, Enforcement mechanism

---

## Coverage Scope

| Option | Description | Selected |
|--------|-------------|----------|
| kb_server/ only | Matches REQUIREMENTS.md | |
| kb_server/ + ingest/ (Recommended) | Both in one pass | ✓ |

**User's choice:** kb_server/ + ingest/
**Notes:** Also decided ingest/ target should be 90% same as kb_server/ (not a gradual ramp).

---

## Uncovered Margin

| Option | Description | Selected |
|--------|-------------|----------|
| Strict 90% — no excludes | Target is 90%+ everywhere, # pragma: no cover seldom | |
| Pragmatic — exclude with justification (Recommended) | Narrow # pragma: no cover with inline comments | ✓ |
| Soft gate — warn but don't fail | Failing build deferred to v1.2 | |

**User's choice:** Pragmatic — exclude with justification
**Notes:** Excludes are inline `# pragma: no cover` only (not centralized in pyproject.toml). Each must have a comment explaining why.

---

## Enforcement Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Both (Recommended) | pyproject.toml fail_under + CI --cov-fail-under | ✓ |
| pyproject.toml only | Simpler single config | |
| CI step only | Pipeline-driven, no pyproject change | |

**User's choice:** Both
**Notes:** Coverage step runs on PR to master only (not every push). CI covers both `--cov=kb_server` and `--cov=ingest`.

---

## Agent's Discretion

- **Logging audit method** — Not discussed. Recommendation: one-time function-collection script, not CI gate.
- **Logging format** — Not discussed. Recommendation: keep stdlib, consistent key=value.

## Deferred Ideas

None.
