# Phase 23: Documentation Overhaul - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Reorganize project documentation by deployment mode (Docker Compose, Helm, Systemd, Manual), update CHANGELOG with v1.3/v1.4 changes, and audit/update REFERENCE.md for accuracy. Existing monolithic topic-based files (OPERATIONS.md, TROUBLESHOOTING.md, INSTRUCTIONS.md) stay intact but gain deployment-mode section headers; a new navigation layer in INDEX.md enables mode-first discovery.

</domain>

<decisions>
## Implementation Decisions

### Doc Structure
- **D-01:** Sections within existing files — Add H2-level deployment-mode headers (`## Docker Compose`, `## Helm`, `## Systemd`, `## Manual`) to existing files (OPERATIONS.md, TROUBLESHOOTING.md, INSTRUCTIONS.md). No split into per-mode directories or files.
- **D-02:** Shared section before mode sections — Add a "Common" H2 section at the top of each file for content that applies to all modes (env vars, architecture, prerequisites). Per-mode H2 sections below.
- **D-03:** Enhance existing INDEX.md — Add a deployment-mode navigation section to `docs/INDEX.md`. Not a new file.
- **D-04:** File-level links in INDEX.md — INDEX.md links to files, not specific H2 section anchors (e.g., `- Docker Compose → docs/OPERATIONS.md, docs/TROUBLESHOOTING.md, docs/INSTRUCTIONS.md`).
- **D-05:** See-also footers — After each mode section within a file, add a cross-reference footer: `See also: [filename] → [section]`.

### README Scope
- **D-06:** Two-tier structure — README has a concise quickstart at top, detailed content moves into `docs/` sub-pages. Not a minimal landing page, not a 50K monolith.
- **D-07:** Quickstart shows all modes — Top section has a "pick your deployment mode" table with 2-3 line summaries per mode and links to `docs/`. No single default mode assumed.
- **D-08:** Multilingual parity — Same two-tier restructuring applies to README.pt-BR.md and README.es.md.

### CHANGELOG Format
- **D-09:** Per-milestone sections — `## [1.3] 2026-05-27` and `## [1.4] 2026-05-27`.
- **D-10:** Plan-level detail within milestones — One bullet per plan within each phase (e.g., `- 22-01: Create integration gap checker script`).

### REFERENCE.md
- **D-11:** Full audit + update — Audit every existing entry for accuracy, update stale descriptions, then add v1.3/v1.4 entries. Not append-only.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — DOCS-01 through DOCS-04 defined for this phase

### Docs to Reorganize
- `docs/INDEX.md` — Enhance with deployment-mode navigation section
- `docs/OPERATIONS.md` — Add Common + per-mode H2 sections, see-also footers
- `docs/TROUBLESHOOTING.md` — Add Common + per-mode H2 sections, see-also footers
- `docs/INSTRUCTIONS.md` — Add Common + per-mode H2 sections, see-also footers
- `docs/REFERENCE.md` — Full audit + update for accuracy and v1.3/v1.4 additions

### Docs to Restructure
- `CHANGELOG.md` — Update with per-milestone (v1.3, v1.4) + per-plan entries
- `README.md` — Two-tier: quickstart at top, detailed content to docs/
- `README.pt-BR.md` — Same two-tier restructuring
- `README.es.md` — Same two-tier restructuring

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/OPERATIONS.md` (34K) — Primary operations reference; already has topic-based sections
- `docs/TROUBLESHOOTING.md` (21K) — Debugging and error resolution per topic
- `docs/INSTRUCTIONS.md` (34K) — Setup and configuration instructions
- `docs/INDEX.md` (4K) — Existing table of contents; will add deployment-mode section
- `docs/REFERENCE.md` (17K) — Quick-reference lookup; needs audit
- `CHANGELOG.md` (30K) — Release history; needs v1.3/v1.4 entries
- `README.md` (50K) / `README.pt-BR.md` (44K) / `README.es.md` (44K) — English + translations

### Established Patterns
- Google-style docstrings and English-only codebase (Phase 12 enforcement)
- Conventional commit format for tracking changes
- 3-language documentation (EN + PT-BR + ES) with parallel structure

### Integration Points
- INDEX.md is the navigation hub for `docs/` directory
- README.md is the repo entry point visible on GitHub
- Cross-reference footers between files create a web of navigation

</code_context>

<specifics>
## Specific Ideas

No specific references or examples were cited. Approach follows standard documentation restructuring patterns with keep-it-simple philosophy (sections in existing files, not new directory trees).

</specifics>

<deferred>
## Deferred Ideas

- **Cross-linking & navigation architecture discussion** — Initially listed as a gray area but user did not select it. Agents have discretion to add sensible cross-references without over-engineering.
- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 23-Documentation-Overhaul*
*Context gathered: 2026-05-27*
