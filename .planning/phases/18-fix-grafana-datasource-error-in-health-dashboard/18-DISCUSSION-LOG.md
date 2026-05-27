# Phase 18: Fix Grafana "Datasource ${DS_PROMETHEUS} was not found" error - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 18-fix-grafana-datasource-error
**Areas discussed:** Fix approach, Scope, __inputs section, Verification

---

## Fix Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Stable UID + hardcoded reference | Add uid to datasource provision, replace all ${DS_PROMETHEUS} with the UID | ✓ |
| Pre-resolve template variable | Keep the template variable but pre-resolve it in the JSON | |
| Name-based reference | Use datasource name "Prometheus" directly instead of UID | |

**User's choice:** Stable UID + hardcoded reference
**Notes:** This is the cleanest approach — no template variable resolution dependency, explicit UID in datasource config.

---

## Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Both config and Helm | Fix deployment/config/ AND deployment/helm/ | ✓ |
| Config only | Only fix the main config copy used by Docker Compose | |

**User's choice:** Both config and Helm

---

## __inputs section

| Option | Description | Selected |
|--------|-------------|----------|
| Remove __inputs entirely | Clean up since provisioning (not UI import) is the deployment path | ✓ |
| Keep __inputs | Preserve for potential UI import compatibility | |

**User's choice:** Remove __inputs entirely

---

## Verification

| Option | Description | Selected |
|--------|-------------|----------|
| Manual verification | Run docker compose up -d, open Grafana UI, confirm no errors | ✓ |
| Add JSON validation | Manual verification + CI check for datasource UID consistency | |
| Just fix, no formal verification | Make the fix, commit, move on | |

**User's choice:** Manual verification

---

## the agent's Discretion

- Exact search-and-replace approach for `${DS_PROMETHEUS}` → `"prometheus"` (sed or script approach for ~60+ occurrences per file)
- Whether to keep or remove the `__requires` section from dashboard JSONs (no functional impact)

## Deferred Ideas

- Prometheus alerting rules — out of scope, belongs in its own phase
- Grafana authentication — Phase 14 decision: anonymous access sufficient
