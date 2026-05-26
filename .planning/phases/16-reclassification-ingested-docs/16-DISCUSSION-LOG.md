# Phase 16: Reclassification capability for document database - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-26
**Phase:** 16-reclassification-ingested-docs
**Areas discussed:** Reclassification scope, Selection mechanism, CLI interface design, Safety & rollback

---

## Reclassification scope

### Question 1: What should be the primary reclassification mode?

| Option | Description | Selected |
|--------|-------------|----------|
| In-place metadata update (Recommended) | Fastest option. Updates vendor/product/subsystem/doc_type/version in Qdrant payload without re-embedding. Keeps existing vectors and chunks. Ideal for classification rule improvements where the document content hasn't changed. | ✓ |
| Full re-ingest | Slowest but most thorough. Re-extracts, re-chunks, re-embeds, and re-indexes. Use when document parsing improved (e.g., better PDF extraction) or chunking strategy changed. Creates fresh vectors. | |
| Hybrid: support both modes | Provides both options via CLI flag (--mode=metadata-only vs --mode=full-reingest). Operators choose based on what changed (classification rules vs extraction logic). | |

**User's choice:** In-place metadata update (Recommended)
**Notes:** User chose the fastest option that preserves embeddings. Full re-ingest deferred for future needs.

### Question 2: Which metadata fields should be updateable during reclassification?

| Option | Description | Selected |
|--------|-------------|----------|
| Classification fields only (vendor, product, subsystem, doc_type, version) | Only update the 5 classification fields that Phase 11 auto-detects: vendor, product, subsystem, doc_type, version. Safest option since these are what the classifier generates. | |
| All metadata fields | Include all metadata fields stored in Qdrant payload: the 5 above plus source_file, chunk_index, timestamp, chunk_text. Allows fixing any incorrect metadata, not just classification. | |
| Classification + optional custom fields | Classification fields by default, but with --include-custom flag to update additional user-defined fields. Extensible for future metadata additions. | ✓ |

**User's choice:** Classification + optional custom fields
**Notes:** Flexible approach allowing extensibility while keeping default behavior focused on classification fields.

### Question 3: How should reclassification handle Qdrant collections?

| Option | Description | Selected |
|--------|-------------|----------|
| Default collection only | Only update documents in the default collection (via CollectionRouter). Simpler UX, fewer edge cases. Operators specify documents via file path or filter, not collection name. | |
| Any collection via --collection flag (Recommended) | Allow operators to specify --collection flag to reclassify in any collection. Useful for multi-tenant setups where different teams have separate collections. | ✓ |
| Support multi-collection reclassification | Single command can reclassify across multiple collections (--all-collections). Most flexible but requires careful filtering to avoid unintended updates. | |

**User's choice:** Any collection via --collection flag (Recommended)
**Notes:** Supports multi-tenant use cases without the risk of accidental multi-collection updates.

### Question 4: How do we handle updates when classification rules improve?

| Option | Description | Selected |
|--------|-------------|----------|
| Manual trigger only | Operator manually triggers reclassification after editing VENDOR_MAP or SUBSYSTEM_PATTERNS in classifier.py. Simple and explicit—no automatic behavior. | |
| Detect changed classifications (Recommended) | Compare current classification against what classify() would return today. Only update documents where classification changed. Efficient but requires running classify() on every document to detect changes. | ✓ |
| Track classifier version | Track classifier.py hash in registry. When hash changes, mark all documents for reclassification review. Automates detection but might over-trigger (e.g., comment-only changes). | |

**User's choice:** Detect changed classifications (Recommended)
**Notes:** Smart detection by comparing current vs. new classification results. More precise than version tracking.

---

## Selection mechanism

### Question 1: How should operators select documents to reclassify?

| Option | Description | Selected |
|--------|-------------|----------|
| File path glob patterns (Recommended) | Operators provide file path patterns like 'docs/WebReports/*.pdf' or 'docs/**/admin*.docx'. Simple and familiar CLI pattern. Works well for targeted updates after editing specific docs. | |
| Metadata filter queries | Filter by current metadata values: --filter vendor='' (empty vendor), --filter product=Unknown, --filter doc_type=general. Useful for finding documents that need classification fixes. | |
| Hybrid: path patterns + metadata filters | Provide both options: path patterns OR metadata filters. Maximum flexibility. Example: 'kb-ingest reclassify docs/OT*.pdf --filter vendor=""' (path + filter combined). | ✓ |
| File list input (--from-file) | Select documents via file containing list of source_file values (one per line). Useful for bulk updates from external analysis or audit reports. | |

**User's choice:** Hybrid: path patterns + metadata filters
**Notes:** Maximum flexibility by supporting both selection mechanisms independently or combined.

### Question 2: How should dry-run / preview work?

| Option | Description | Selected |
|--------|-------------|----------|
| Mandatory dry-run before execution | Always require --dry-run first, then --confirm to execute. Two-step process prevents accidents. Example: '...reclassify --dry-run' (shows changes) then '...reclassify --confirm' (applies them). | |
| Interactive confirmation with preview (Recommended) | Show preview by default, then prompt 'Apply these changes? [y/N]'. Interactive confirmation. One command, built-in safety. Use --yes to skip prompt for automation. | ✓ |
| Execute immediately (--dry-run optional) | Execute immediately by default. Operators use --dry-run if they want to preview first. Fastest for experienced users but riskier. | |

**User's choice:** Interactive confirmation with preview (Recommended)
**Notes:** Balances safety (preview + confirmation) with convenience (single command). --yes flag for automation.

### Question 3: What detail level should the preview show?

| Option | Description | Selected |
|--------|-------------|----------|
| Full per-document diff | Show full diff for each document: 'docs/OT-WebReports-Admin.pdf: vendor="" → "OpenText", product="WebReports" (unchanged), subsystem="" → "Admin"'. Most detailed but verbose for large batches. | |
| Aggregated summary by field (Recommended) | Group changes by type: 'vendor: 47 documents ("" → "OpenText"), subsystem: 23 documents ("" → "Admin"), product: 0 changes'. Compact summary shows impact at a glance. | ✓ |
| Summary + verbose mode | Show both: aggregated summary first, then optional --verbose flag for per-document details. Best of both worlds—quick overview + drill-down capability. | |

**User's choice:** Aggregated summary by field (Recommended)
**Notes:** Compact and clear. --verbose mode left as agent's discretion for future enhancement.

### Question 4: What if source files no longer exist on disk?

| Option | Description | Selected |
|--------|-------------|----------|
| Skip missing files with warning (Recommended) | Skip documents that are missing on disk with a warning: 'Warning: source_file not found, skipping: docs/deleted.pdf'. Only reclassify documents that still exist in the filesystem. | ✓ (partial) |
| Allow reclassification without source file | Reclassify all matched documents in Qdrant regardless of disk presence. Useful when source files moved/renamed. Classification logic doesn't need the file—only the existing metadata. | |
| Configurable via --allow-missing flag | Provide --allow-missing flag. Default behavior skips missing files, but flag enables reclassification when operators know files moved. Explicit opt-in for flexibility. | ✓ (partial) |

**User's choice:** Skip missing files with warning + --allow-missing flag
**Notes:** User combined two options: default skip with warning (safe), plus --allow-missing flag (flexible). Balances safety with operator control.

---

## CLI interface design

### Question 1: Where should the reclassification command live in the CLI?

| Option | Description | Selected |
|--------|-------------|----------|
| New subcommand: kb-ingest reclassify (Recommended) | New top-level subcommand: 'kb-ingest reclassify <pattern> [options]'. Follows existing structure (kb-ingest job, kb-ingest db, kb-ingest export). Clear separation from normal ingest operations. | ✓ |
| Flag on existing ingest command | Extend existing ingest command: 'kb-ingest --docs <path> --reclassify-only'. Reuses existing path logic but adds flag for metadata-only mode. Less discoverable. | |
| Separate kb-reclassify command | New script: 'kb-reclassify <pattern> [options]'. Separate entry point (added to setup.py). Independent from ingest workflow. Simpler for users who only want reclassification. | |

**User's choice:** New subcommand: kb-ingest reclassify (Recommended)
**Notes:** Consistent with existing CLI structure and clearly separates concerns.

### Question 2: What arguments should be required vs optional?

| Option | Description | Selected |
|--------|-------------|----------|
| Required pattern argument (Recommended) | Pattern is required: 'kb-ingest reclassify <pattern>'. Forces explicit selection. All flags are optional: --collection, --filter, --yes, --allow-missing, --include-custom. Clear and safe. | ✓ |
| All optional (smart defaults) | All arguments optional: 'kb-ingest reclassify' defaults to showing preview of all documents needing reclassification (where current metadata differs from classify() output). Convenient but might be surprising. | |
| Require pattern OR --filter | Require either pattern OR --filter: 'kb-ingest reclassify <pattern>' or 'kb-ingest reclassify --filter vendor=""'. Forces explicit selection via one of the two mechanisms. | |

**User's choice:** Required pattern argument (Recommended)
**Notes:** Explicit selection requirement prevents accidental mass operations.

### Question 3: How should progress be reported for large batches (1000+ documents)?

| Option | Description | Selected |
|--------|-------------|----------|
| Rich progress bar (Recommended) | Use Rich progress bar (already in stack via 'kb-ingest status'): '[=========>  ] 450/1000 documents reclassified (45%) ETA: 2m 15s'. Clean, real-time, familiar to users. | |
| Periodic log messages | Log-based progress: 'Reclassified 100/1000 documents...' every N documents. Simpler but less visual. Works well for scripted/automated runs. | |
| Rich progress + --no-progress flag | Both: Rich progress bar by default, log messages with --no-progress for automation. Best of both worlds—interactive + scriptable. | ✓ |

**User's choice:** Rich progress + --no-progress flag
**Notes:** Interactive mode gets visual progress, automation gets clean logs. Reuses existing Rich infrastructure.

### Question 4: Should reclassification create an audit log of changes?

| Option | Description | Selected |
|--------|-------------|----------|
| Write detailed log file (Recommended) | Write detailed change log to file: 'reclassify-2026-05-26-15-30-00.log' with before/after metadata for every updated document. Stored in logs/ directory. Full audit trail. | |
| Summary to stdout only | Only log summary to stdout: 'Reclassified 47 documents. vendor: 47 updates, subsystem: 23 updates, product: 0 updates.' No persistent record unless operator redirects output. | |
| SQLite audit table in registry.db | SQLite audit table: Create 'reclassify_history' table in registry.db with timestamp, source_file, field_name, old_value, new_value. Queryable audit history. Integrated with existing registry. | ✓ |

**User's choice:** SQLite audit table in registry.db
**Notes:** Queryable audit history integrated with existing registry infrastructure. More structured than log files.

---

## Safety & rollback

### Question 1: How should we backup metadata before reclassification?

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite backup before update (Recommended) | Before updating Qdrant, write old metadata to 'reclassify_backups' SQLite table with timestamp. Rollback via 'kb-ingest reclassify rollback --session <timestamp>'. Full undo capability. | ✓ |
| Qdrant collection snapshots | Qdrant supports point-in-time snapshots. Take snapshot before reclassification, restore from snapshot if needed. Native Qdrant feature but requires operator to manage snapshots. | |
| Audit log only (no backup) | No automatic backup. Audit log (from CLI Design area) provides history but not undo. Operators rely on --dry-run preview. Simplest implementation, higher risk. | |

**User's choice:** SQLite backup before update (Recommended)
**Notes:** Full undo capability integrated with existing registry infrastructure.

### Question 2: How should operators verify reclassification worked correctly?

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated verify subcommand (Recommended) | Add 'kb-ingest reclassify verify <pattern>' command: compares current Qdrant metadata against classify() output for selected documents. Shows mismatches. Useful before and after reclassification. | ✓ |
| Automatic post-update verification | Automatic post-reclassification check: after updating Qdrant, re-run classify() on updated documents and confirm metadata matches. Built into reclassify command. Catches implementation bugs. | |
| Manual verification (no new command) | Manual verification via existing MCP tools: operators use 'list_documents' or 'get_chunk' to spot-check updated metadata. No new code needed but less structured. | |

**User's choice:** Dedicated verify subcommand (Recommended)
**Notes:** Explicit verification command allows pre-flight checks before reclassify and post-flight validation.

### Question 3: What should the rollback command interface look like?

| Option | Description | Selected |
|--------|-------------|----------|
| Session-based rollback (Recommended) | List sessions: 'kb-ingest reclassify sessions' shows all backup sessions with timestamps and document counts. Rollback specific session: '...rollback --session 2026-05-26-15-30-00'. Explicit and safe. | ✓ (partial) |
| Rollback last operation | Rollback last N operations: '...rollback --last 1' (undo last reclassify). Simple but risky if multiple people use the system. No explicit session selection. | |
| Pattern + timestamp rollback | Rollback by document pattern: '...rollback docs/WebReports/*.pdf --before "2026-05-26 15:30"'. Restore specific documents to metadata state before given timestamp. Most granular. | ✓ (partial) |

**User's choice:** Session-based + pattern + timestamp rollback
**Notes:** User combined both approaches: session-based for full rollback, pattern+timestamp for selective rollback. Maximum flexibility.

### Question 4: How long should backup metadata be retained?

| Option | Description | Selected |
|--------|-------------|----------|
| 30-day retention with auto-cleanup (Recommended) | Keep backups for 30 days by default (configurable via RECLASSIFY_BACKUP_RETENTION_DAYS env var). Auto-cleanup on each reclassify run. Balances safety with disk usage. | ✓ |
| Keep indefinitely (manual cleanup) | Keep backups indefinitely. Manual cleanup via 'kb-ingest reclassify clean-backups --before <date>'. Full audit trail but requires operator discipline. | |
| Keep last N sessions | Keep only last N backup sessions (e.g., N=10). Rolling window. Simple but might lose important history if many reclassifications happen. | |

**User's choice:** 30-day retention with auto-cleanup (Recommended)
**Notes:** Balances safety with disk usage. Configurable via env var for site-specific needs.

---

## the agent's Discretion

The following areas were left to the agent's discretion during implementation:

- Exact SQL schema for `reclassify_backups` and `reclassify_history` tables (columns, indexes, constraints)
- Rich progress bar layout and update frequency
- Error handling strategy for Qdrant update failures (partial rollback, continue-on-error flag)
- Whether to support regex patterns in addition to glob patterns for file selection
- Whether `--verbose` flag for per-document diff is needed (preview currently shows aggregated summary only per D-07)

---

## Deferred Ideas

**Full re-ingest mode:** Discussed as alternative to in-place metadata update but deferred. Current use case (applying improved classification rules) only requires metadata updates. If document parsing or chunking changes in the future, full re-ingest mode could be added via `--mode=full-reingest` flag or as a separate phase.

---

*Phase 16: Reclassification capability for document database*
*Discussion date: 2026-05-26*
