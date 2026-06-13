# Phase 23: Documentation Overhaul - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 23-Documentation-Overhaul
**Areas discussed:** Doc structure approach, README scope, CHANGELOG format, REFERENCE.md update scope, INDEX.md cross-linking depth, Cross-linking between files

---

## Doc Structure Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Split into per-mode dirs | docs/deploy/docker-compose/, docs/deploy/helm/, etc. | |
| Per-mode files in docs/ root | docs/DOCKER_COMPOSE.md, docs/HELM.md, etc. | |
| Sections within existing files | Add H2 headers to OPERATIONS.md, TROUBLESHOOTING.md, INSTRUCTIONS.md | ✓ |

**User's choice:** Sections within existing files
**Notes:** Keep monolithic files but reorganize with deployment-mode section headers

| Option | Description | Selected |
|--------|-------------|----------|
| New docs/DEPLOYMENT_INDEX.md | Standalone file for deployment navigation | |
| Enhance existing INDEX.md | Add deployment-mode section to existing INDEX.md | ✓ |
| README as landing page | Put navigation at top of README | |

**User's choice:** Enhance existing INDEX.md

| Option | Description | Selected |
|--------|-------------|----------|
| H2-level headers per mode | ## Docker Compose, ## Helm, etc. | ✓ |
| H1-level with mode badges | # Docker Compose 🐳, etc. | |
| Tab-style labeled sections | HTML comments or visual separators | |

**User's choice:** H2-level headers per mode

| Option | Description | Selected |
|--------|-------------|----------|
| Shared section before mode sections | "Common" H2 at top of each file | ✓ |
| Deduplicate per-mode | Self-contained per mode but redundant | |

**User's choice:** Shared section before mode sections

---

## README Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Keep comprehensive | 50K fine as single-file reference | |
| Slim to landing page | Minimal intro + links to docs/ | |
| Two-tier: quickstart + full | Concise quickstart + docs/ sub-pages | ✓ |

**User's choice:** Two-tier: quickstart + full

| Option | Description | Selected |
|--------|-------------|----------|
| Quickstart: single path only | README assumes Docker Compose | |
| Quickstart: all modes links | Pick-your-mode table with links | ✓ |
| Minimal README + deploy docs | Just project intro + badges | |

**User's choice:** Quickstart with all modes links

| Option | Description | Selected |
|--------|-------------|----------|
| Same two-tier restructuring | Apply to pt-BR and es | ✓ |
| Keep pt-BR and es as-is | Only restructure English | |

**User's choice:** Same two-tier restructuring

---

## CHANGELOG Format

| Option | Description | Selected |
|--------|-------------|----------|
| Per-milestone sections | ## [1.3], ## [1.4] | ✓ |
| Per-phase subsections | ## Phase 22, ## Phase 23, etc. | |

**User's choice:** Per-milestone sections

| Option | Description | Selected |
|--------|-------------|----------|
| Phase-level summaries | One bullet per phase | |
| Plan-level details | One bullet per plan within phase | ✓ |
| Key change list | Actual changed files/features | |

**User's choice:** Plan-level details

---

## REFERENCE.md Update Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Append-only: new entries | Add sections for v0.1.3/v0.1.4 only | |
| Full audit + update | Audit every entry for accuracy then add | ✓ |

**User's choice:** Full audit + update

---

## INDEX.md Cross-linking Depth

| Option | Description | Selected |
|--------|-------------|----------|
| File-level links only | - Docker Compose → docs/OPERATIONS.md | ✓ |
| H2 section-level references | Include section anchor references | |
| Full topic map | Table with modes as columns | |

**User's choice:** File-level links only

---

## Cross-linking Between Files

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, with see-also footers | After each mode section: "See also: TROUBLESHOOTING.md → Docker Compose" | ✓ |
| No, INDEX.md is sufficient | Single navigation source | |

**User's choice:** Yes, with see-also footers

---

## Deferred Ideas

None — discussion stayed within phase scope.
