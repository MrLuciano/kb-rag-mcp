# Phase 5: SSE Stability & Python 3.13 Compatibility - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-21
**Phase:** 5-SSE Stability & Python 3.13 Compatibility
**Areas discussed:** SSE test strategy, CI matrix design, Starlette version policy, Compatibility audit scope

---

## SSE Test Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Unit test only | Mock connect_sse, verify Response() returned. Fast, no deps. | |
| Integration test only | Use Starlette TestClient to simulate SSE connect/disconnect. More realistic. | |
| Both unit + integration | Unit for handler→Response contract, integration for end-to-end crash/no-crash. | ✓ |

**User's choice:** Both unit + integration tests

---

## CI Matrix Design

| Option | Description | Selected |
|--------|-------------|----------|
| GitHub Actions matrix | strategy.matrix.python-version in ci.yml. Simplest, parallel on push/PR. | ✓ |
| tox + CI | Define matrix in tox.ini, call tox from CI. Portable but extra layer. | |
| Expand single job | Sequential version runs. Simpler output but slower. | |

**User's choice:** GitHub Actions matrix
**Notes:** Also include Python 3.12 in the matrix

---

## Starlette Version Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Pin minimum + document | Add >=1.0.0 to requirements.in, document in STACK.md. | ✓ |
| Exact pin | =1.0.0 in requirements.txt. Most predictable. | |
| Don't pin — rely on CI | Let matrix catch breaking changes automatically. | |

**User's choice:** Pin minimum + document

---

## Compatibility Audit Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Fix what CI fails on | Add 3.13 + 3.12 to matrix, fix failures. | |
| CI failures + dependency audit | Also run pip-compile --python-version 3.13 proactively. | ✓ |
| Full proactive scan + CI | Grep for 3.11-only patterns AND run CI. | |

**User's choice:** CI failures + dependency audit

---

## Deferred Ideas

None — discussion stayed within phase scope.
