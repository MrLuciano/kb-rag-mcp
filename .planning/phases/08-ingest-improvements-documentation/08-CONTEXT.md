# Phase 8: Ingest Improvements & Documentation - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver four improvements:
1. OTCS documents auto-tagged by product area (INGEST-01)
2. `kb-ingest status` CLI command showing live ingest stats (INGEST-02)
3. English docstrings for all public APIs across `kb_server/` and `ingest/` (DOC-01)
4. Updated `docs/` reflecting v1.1 (DOC-02)

Requirements: INGEST-01, INGEST-02, DOC-01, DOC-02

</domain>

<decisions>
## Implementation Decisions

### OTCS Product Detection (INGEST-01)

- **D-01:** Expanded product set — cover WebReports, xECM, Workflow, CSIDE plus
  other OTCS product areas (Content Server, Brava, OT2, Document Viewer,
  API Gateway, etc.). Researcher should enumerate the full OTCS product lineup
  and verify with the user.
- **D-02:** Detection approach — both directory name and filename pattern
  matching, with directory taking priority. This extends the existing
  `infer_product()` strategy.
- **D-03:** OTCS aliases go inline in `ingest/classifier.py` — extend
  `PRODUCT_ALIASES` and `PRODUCT_FROM_NAME` tables directly. No separate file.

### Docstrings Pass (DOC-01)

- **D-04:** Full sweep — translate existing Portuguese docstrings to English
  AND fill all gaps on undocumented public functions/classes.
- **D-05:** Full Google-style docstrings — one-line summary + Args + Returns
  + Raises sections where applicable.
- **D-06:** Gap finding via automated script (similar to `logging-audit.py`),
  fixing in bulk after the script identifies all gaps.

### Documentation Content (DOC-02)

- **D-07:** Full docs refresh — review and update all 22 existing docs for
  v1.1 accuracy, not just the 3 required sections.
- **D-08:** Architecture diagrams in Mermaid (text-based, markdown-embedded)
  — not images or drawio.

### Areas Not Discussed (agent discretion)

- **CLI Status Command (INGEST-02)** — Not selected for discussion.
  Recommendation: extend `ingest/cli/main.py` with a `status` command that
  queries `IngestRegistry` SQLite for file counts and Qdrant for chunk counts.
  Use Rich for formatted table output. Support optional `--source` filter.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §"Ingest Improvements" — INGEST-01, INGEST-02
- `.planning/REQUIREMENTS.md` §"Documentation" — DOC-01, DOC-02
- `.planning/ROADMAP.md` §"Phase 8" — Phase 8 goal, success criteria, plan stubs

### Codebase Maps
- `.planning/codebase/STRUCTURE.md` — Module layout for kb_server/ and ingest/
- `.planning/codebase/CONVENTIONS.md` — Docstring conventions, naming style
- `.planning/codebase/STACK.md` — Dependencies (click, typer, rich, etc.)

### Source Files
- `ingest/classifier.py` — Existing classifier; extend PRODUCT_ALIASES and
  PRODUCT_FROM_NAME for OTCS products
- `ingest/cli/main.py` — Click-based CLI; add `status` subcommand here
- `ingest/core/metadata.py` — `IngestRegistry` with summary(), list_errors(),
  list_all() methods for status data
- `kb_server/vector_store.py` — Qdrant abstraction; get_stats() for chunk
  counts from live Qdrant

### Existing Docs
- `docs/ARCHITECTURE.md` (planned — new Mermaid diagram)
- `docs/OPERATIONS.md` — Update for v1.1 remote deployment
- `docs/INDEX.md` — Review and update

### Prior Phase Context
- `.planning/phases/07-logging-quality-gate-coverage-enforcement/07-CONTEXT.md`
- `.planning/phases/06-test-coverage-isolation/06-CONTEXT.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ingest/classifier.py` — `infer_product()`, `infer_doc_type()`, `classify()`
  functions with existing PRODUCT_ALIASES / PRODUCT_FROM_NAME tables ready to
  extend. `infer_product()` already implements directory-first, filename-fallback
  logic.
- `ingest/cli/main.py` — Existing `info` command shows Click-based CLI pattern
  for querying MetadataStore/IngestRegistry. Reusable as template for `status`.
- `ingest/core/metadata.py` — `IngestRegistry.summary()` returns total/ok/error/
  deleted/chunks counts. `list_all()` supports status filtering.
- `scripts/logging-audit.py` — AST-based scanner pattern reusable for docstring
  audit script.
- `docs/` — 22 existing documents can serve as templates and consistency check.

### Established Patterns
- **CLI:** Click-based with `@click.group()` / `@cli.command()` pattern.
  Rich not yet used in CLI but available in dependencies (`rich==14.3.4`).
- **Docstrings:** Some Google-style (Args/Returns), some one-line, some
  Portuguese. CONVENTIONS.md specifies Google-style but it's inconsistently
  applied.
- **Logging audit pattern:** `scripts/logging-audit.py` shows AST-based scanning
  approach — can be adapted for docstring checking.

### Integration Points
- `ingest/classifier.py` — Extend PRODUCT_ALIASES with OTCS directory names
  (webreports/, xecm/, workflow/, cside/); extend PRODUCT_FROM_NAME with
  OTCS filename patterns
- `ingest/cli/main.py` — Add `status` subcommand; add to `cli.add_command()`
- All 30+ modules in `kb_server/` and `ingest/` — Docstring sweep needs to
  touch every one

### Targeting Identified
- OTCS product list needs research — user said "expanded set" but researcher
  should enumerate full lineup
- ~30 Python source modules need docstring audit + bulk fix
- 22 existing docs need v1.1 accuracy review

</code_context>

<specifics>
## Specific Ideas

- Docstring audit script: adapted from `scripts/logging-audit.py` — scan for
  public defs/classes, check for docstring presence, output gap report
- OTCS mapping: directory folders named `WebReports/`, `xECM/`, `Workflow/`,
  `CSIDE/` would be auto-detected by the existing `infer_product()` directory
  logic without code changes — just need to add aliases
- Status command: `kb-ingest status` with Rich table showing:
  ```
  Source       | Files | Chunks | Errors | Last Ingest
  webreports/  |   142 |   3890 |      3 | 2026-05-22
  xecm/        |    89 |   2104 |      1 | 2026-05-22
  ```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 8-Ingest Improvements & Documentation*
*Context gathered: 2026-05-23*
