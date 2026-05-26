# Phase 16: Reclassification capability for document database - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Provide a mechanism to reclassify already-ingested documents when classification logic improves. Enables operators to update metadata (vendor/product/subsystem/doc_type/version) in the Qdrant vector database without re-processing and re-embedding documents. Builds on Phase 11's auto-classification system to allow operators to apply improved classification rules to ~585 documents already indexed before Phase 11 shipped.

</domain>

<decisions>
## Implementation Decisions

### Reclassification Scope
- **D-01:** Primary mode is **in-place metadata update** — updates vendor/product/subsystem/doc_type/version in Qdrant payload without re-embedding. Preserves existing vectors and chunks. Ideal for classification rule improvements where document content hasn't changed.
- **D-02:** Updateable fields are **classification fields by default** (vendor, product, subsystem, doc_type, version), with **--include-custom flag** to update additional user-defined fields. Extensible for future metadata additions.
- **D-03:** Support **any collection via --collection flag** — allows operators to reclassify in specific collections. Useful for multi-tenant setups where different teams have separate collections.
- **D-04:** **Detect changed classifications** — compare current Qdrant metadata against what `classify()` would return today. Only update documents where classification changed. Efficient but requires running `classify()` on every matched document to detect changes.

### Selection Mechanism
- **D-05:** **Hybrid selection** — support both file path glob patterns (e.g., `docs/WebReports/*.pdf`) AND metadata filter queries (e.g., `--filter vendor=""`). Can combine: `kb-ingest reclassify docs/OT*.pdf --filter vendor=""`. Maximum flexibility.
- **D-06:** **Interactive confirmation with preview** — show aggregated summary of changes by field (e.g., "vendor: 47 documents ('' → 'OpenText'), subsystem: 23 documents ('' → 'Admin')") then prompt "Apply these changes? [y/N]". Use `--yes` flag to skip prompt for automation.
- **D-07:** Preview shows **aggregated summary by field** — group changes by metadata field with counts. Compact summary shows impact at a glance. No per-document diff unless `--verbose` flag added in future.
- **D-08:** **Skip missing files with warning** by default (when source_file not found on disk). Provide **--allow-missing flag** to enable reclassification when operators know files moved or want to rely on existing Qdrant metadata alone. Balances safety with flexibility.

### CLI Interface Design
- **D-09:** New subcommand: **kb-ingest reclassify** — follows existing structure (kb-ingest job, kb-ingest db, kb-ingest export). Clear separation from normal ingest operations.
- **D-10:** **Required pattern argument** — `kb-ingest reclassify <pattern>` forces explicit selection. All flags are optional: `--collection`, `--filter`, `--yes`, `--allow-missing`, `--include-custom`. Clear and safe.
- **D-11:** Progress reporting uses **Rich progress bar by default** (already in stack via `kb-ingest status`), with **--no-progress flag** for automation/scripting. Interactive + scriptable.
- **D-12:** **SQLite audit table in registry.db** — create `reclassify_history` table with (timestamp, source_file, field_name, old_value, new_value). Queryable audit history integrated with existing registry. NOT a separate log file.

### Safety & Rollback
- **D-13:** **SQLite backup before update** — write old metadata to `reclassify_backups` table in registry.db with session timestamp before updating Qdrant. Enables full undo capability via rollback command.
- **D-14:** **Dedicated verify subcommand** — `kb-ingest reclassify verify <pattern>` compares current Qdrant metadata against `classify()` output for selected documents. Shows mismatches. Useful before and after reclassification.
- **D-15:** **Session-based rollback PLUS pattern + timestamp rollback** — `kb-ingest reclassify sessions` lists all backup sessions. `kb-ingest reclassify rollback --session <timestamp>` restores full session. `kb-ingest reclassify rollback <pattern> --before <timestamp>` restores specific documents to metadata state before given time. Supports both full and selective undo.
- **D-16:** **30-day backup retention with auto-cleanup** — keep backups for 30 days by default (configurable via `RECLASSIFY_BACKUP_RETENTION_DAYS` env var). Auto-cleanup on each reclassify run. Balances safety with disk usage.

### the agent's Discretion
- Exact SQL schema for `reclassify_backups` and `reclassify_history` tables (columns, indexes, constraints)
- Rich progress bar layout and update frequency
- Error handling strategy for Qdrant update failures (partial rollback, continue-on-error flag)
- Whether to support regex patterns in addition to glob patterns for file selection
- Whether `--verbose` flag for per-document diff is needed (preview currently shows aggregated summary only per D-07)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Classification System (Phase 11)
- `ingest/classifier.py` — Auto-classification logic: `classify()`, `infer_vendor()`, `infer_subsystem()`, `enrich_classification()`, `VENDOR_MAP`, `SUBSYSTEM_PATTERNS`, `DOC_TYPE_RULES`. 865 lines. Core logic to be reused for reclassification detection.
- `.planning/phases/11-auto-classification/11-SUMMARY.md` — Phase 11 deliverables: vendor/subsystem inference, metadata extraction from PDF/DOCX, enrichment, ingest integration. Context for what already exists.

### Vector Store & Registry
- `kb_server/vector_store.py` — `VectorStore` class with async Qdrant operations (`search`, `upsert_chunks`, `list_documents`). Will need new methods for metadata-only updates.
- `ingest/registry.py` — `IngestRegistry` SQLite tracking (`needs_ingest`, `mark_ok`, `mark_error`). Schema: `data/registry.db`. Will add `reclassify_backups` and `reclassify_history` tables here.

### CLI Framework
- `ingest/cli/main.py` — Typer CLI with subcommands (job, db, export, progress, legacy). New `reclassify` subcommand will be added here.
- `ingest/ingest.py` — Ingest orchestrator: file scanning, classification, chunking, embedding, upserting. Lines 410-459 show how vendor/subsystem are stored in chunk payload.

### Codebase Architecture
- `.planning/codebase/ARCHITECTURE.md` — Ingest Flow (lines 86-95): `classifier.classify(file)` → `VectorStore.upsert_chunks()` → `IngestRegistry.mark_ok()`. Reclassification will bypass extraction/chunking/embedding steps.
- `.planning/codebase/STACK.md` — Dependencies: `qdrant-client==1.18.0`, `rich==14.3.4`, `SQLAlchemy==2.0.49`, `typer==0.25.1`. All needed libraries already in stack.

### Project Constraints
- `.planning/PROJECT.md` — Constraints: CLI backward-compatible, no authentication, test baseline 585 tests (no regressions), English-only comments/docstrings, TDD mandatory for behavior changes.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`ingest/classifier.py:classify()`** — 865-line classification module with `infer_vendor()`, `infer_subsystem()`, `infer_product()`, `infer_doc_type()`, `infer_version()`, `enrich_classification()`. Can reuse this entire pipeline for reclassification detection (run classify() on source_file path, compare result to Qdrant metadata).
- **`kb_server/vector_store.py:VectorStore`** — Async Qdrant client wrapper with `search()`, `upsert_chunks()`, `list_documents()`. Will need new method like `update_metadata(collection_name, filters, updates)` for in-place payload updates.
- **`ingest/registry.py:IngestRegistry`** — SQLite abstraction with `needs_ingest()`, `mark_ok()`, `mark_error()`. Schema at `data/registry.db`. Will add two new tables: `reclassify_backups` (for rollback) and `reclassify_history` (for audit).
- **`ingest/cli/main.py`** — Typer CLI framework with Rich progress bars already used in `kb-ingest status`. Can reuse Rich table/progress patterns for reclassify preview and progress reporting.

### Established Patterns
- **SQLite for tracking** — Registry uses SQLite (`data/registry.db`) for file hashes, chunk counts, timestamps. Reclassify backup/audit tables will live in same database for consistency.
- **Async everywhere** — All Qdrant operations are async (`AsyncQdrantClient`). Reclassify logic must be async.
- **Typer subcommands** — CLI uses Typer with subcommands: `kb-ingest job`, `kb-ingest db`, `kb-ingest export`. New `kb-ingest reclassify` follows same pattern.
- **Rich for UI** — `kb-ingest status` uses Rich tables and progress bars. Reclassify preview (aggregated summary) and progress reporting will use Rich.
- **Metadata in chunk payload** — Phase 11 stores vendor/subsystem in Qdrant chunk payload alongside product/doc_type/version (see `ingest/ingest.py:459`). Reclassify updates same payload fields.

### Integration Points
- **Qdrant collection routing** — `CollectionManager` / `CollectionRouter` resolve collection names. Reclassify `--collection` flag will use `CollectionRouter.resolve()`.
- **Ingest registry** — `IngestRegistry` tracks which files have been ingested. Reclassify will query registry to validate source files exist (unless `--allow-missing` flag).
- **Classifier metadata detection** — `classifier.classify(file_path)` returns dict with vendor/product/subsystem/doc_type/version. Reclassify compares this against Qdrant metadata to detect changes.

</code_context>

<specifics>
## Specific Ideas

### Command Examples
User envisions these command patterns:

```bash
# Reclassify all WebReports documents with empty vendor
kb-ingest reclassify 'docs/WebReports/*.pdf' --filter vendor=""

# Reclassify specific collection
kb-ingest reclassify 'docs/OTCS/*.docx' --collection otcs-docs

# Dry-run preview (shows aggregated summary, prompts for confirmation)
kb-ingest reclassify 'docs/**/*.pdf'
# Output: "vendor: 47 documents ('' → 'OpenText'), subsystem: 23 documents..."
# Prompt: "Apply these changes? [y/N]"

# Automation (skip prompt)
kb-ingest reclassify 'docs/**/*.pdf' --yes --no-progress

# Allow reclassification when source files moved
kb-ingest reclassify 'docs/**/*.pdf' --allow-missing

# Verify classification accuracy before reclassifying
kb-ingest reclassify verify 'docs/WebReports/*.pdf'

# List backup sessions
kb-ingest reclassify sessions

# Rollback entire session
kb-ingest reclassify rollback --session 2026-05-26-15-30-00

# Rollback specific documents to state before timestamp
kb-ingest reclassify rollback 'docs/WebReports/*.pdf' --before "2026-05-26 15:30"
```

### SQLite Schema Additions
Two new tables in `data/registry.db`:

**reclassify_backups** (for rollback):
- session_timestamp (PK, TEXT) — ISO timestamp when reclassify session started
- source_file (PK, TEXT) — file path
- field_name (PK, TEXT) — vendor/product/subsystem/doc_type/version
- old_value (TEXT) — metadata value before reclassify
- chunk_index (INTEGER) — which chunk within document (nullable if backup is at document level)

**reclassify_history** (for audit):
- id (PK, INTEGER AUTOINCREMENT)
- timestamp (TEXT) — ISO timestamp
- source_file (TEXT) — file path
- field_name (TEXT) — which metadata field changed
- old_value (TEXT) — before
- new_value (TEXT) — after
- session_timestamp (TEXT) — links to reclassify_backups session (FK)

### Rich Preview Format
Aggregated summary example:

```
╭─────────────────────────────────────────────────────────────────╮
│ Reclassification Preview                                        │
├─────────────────────────────────────────────────────────────────┤
│ Pattern:     docs/**/*.pdf                                      │
│ Collection:  kb-default                                         │
│ Documents:   127 matched                                        │
├─────────────────────────────────────────────────────────────────┤
│ Changes:                                                        │
│   vendor:     47 documents  ("" → "OpenText")                   │
│   subsystem:  23 documents  ("" → "Admin", "" → "API")          │
│   product:     0 documents  (no changes)                        │
│   doc_type:    3 documents  ("general" → "admin_guide")         │
│   version:     0 documents  (no changes)                        │
├─────────────────────────────────────────────────────────────────┤
│ Backup:      Session 2026-05-26-15-30-00 will be created       │
╰─────────────────────────────────────────────────────────────────╯

Apply these changes? [y/N]:
```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

Full re-ingest mode (D-01 chose in-place metadata update as primary mode) was discussed but deferred. If needed in the future, it could be added as a separate mode flag (`--mode=full-reingest`) or a different phase. Current use case (applying improved classification rules) only requires metadata updates, not re-embedding.

</deferred>

---

*Phase: 16-reclassification-ingested-docs*
*Context gathered: 2026-05-26*
