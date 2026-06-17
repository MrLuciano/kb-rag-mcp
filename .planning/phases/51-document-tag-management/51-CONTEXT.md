# Phase 51 — Document Tag Management & Re-ingest Control

## Context Source

ROADMAP.md Phase 51 definition + user discussion 2026-06-17 + existing v0.1.5 infrastructure.

## What This Is

A bulk classification tag editor that lets admins correct misclassified documents after ingestion. Unlike Phase 16 (reclassification — which re-runs the classifier and updates metadata in-place), Phase 51 provides manual tag editing: add, remove, or overwrite tags on documents, with the option to mark files for re-ingestion.

## Why Now

v0.1.5 has a full Admin SPA with auth, document browsing, and bulk actions. The final gap is letting admins fix classification mistakes without re-running the full ingest pipeline. This completes the document lifecycle management story: ingest → browse → correct → re-ingest.

## Depends On

- Phase 28c (Admin SPA shell) — UI framework, auth gating, HTMX partials
- Phase 45 (Registry bulk operations) — SQLite registry bulk update patterns
- Phase 16 (Reclassification) — In-place metadata update API on VectorStore

## Key Design Decisions (Locked)

### D-01: Tag Scope — Document-Level
Tags apply to the entire document, not individual chunks. All chunks of a document share the same tags. Simpler mental model for admins.

### D-02: Tag vs Classification — Visually Separate
Tags are displayed in a dedicated column/badges area, distinct from auto-classified fields (product, type, version, vendor, subsystem, module). Tags complement classification, never replace it.

### D-03: Tag Format — Minimal Validation
- Max 50 characters
- No whitespace allowed
- Case-insensitive (stored lowercase, prevents 'Legacy' vs 'legacy' duplicates)
- Free-form strings, not tied to classifier taxonomy

### D-04: UI Placement — Both Inline and Dedicated
- **Inline**: Tag editing available in existing `/admin/documents` browse table (add/remove tags per row, bulk toolbar actions)
- **Dedicated**: `/admin/tags` tab for heavy tag management (filter by tag, bulk cleanup, merge tags, find untagged)

### D-05: Re-ingest Trigger — Queue as Background Job
When admin marks documents for re-ingest, create a background job and show progress in the existing Jobs tab. Non-blocking, uses existing job infrastructure.

### D-06: Tag Search — Opt-in Searchable
Tags are stored in Qdrant payload but NOT indexed for search by default. Search integration can be enabled later via config toggle without migration.

### D-07: Audit Log — Minimal
Each tag mutation logs: user ID, timestamp, document path, action (add/remove/replace), tag values. One entry per document mutation.

### D-08: Migration — Lazy
No bulk migration script. Tags field added to Qdrant payload on first edit. Registry schema updated at deploy time (SQLite ALTER TABLE). Documents without tags show "No tags".

### D-09: Error Handling — Best-Effort Bulk Operations
Apply what succeeds, report failures at end. Summary format: "97 updated, 3 failed: [list]". Matches existing reclassify CLI pattern.

### D-10: Tag Visuals — Plain Bootstrap Badges
All tags use consistent Bootstrap badge styling. No color management, no categorization. Simple and uniform.

### D-11: Tag Limits — Max 20 Per Document
Enforced at API level. Prevents tag spam while allowing generous tagging.

### D-12: Tag Autocomplete — Yes
Tag input fields show dropdown with existing tags as you type. Prevents duplicates and improves consistency.

### D-13: Tag Deletion — Cascade
Deleting a tag from the system removes it from all documents that had it. Clean, predictable behavior.

## Requirements

| ID | Description | Source |
|----|-------------|--------|
| TAG-01 | `kb-rag tags list` shows tag counts (Product, Type, Version, Status) | ROADMAP |
| TAG-02 | `kb-rag tags update --dry-run` previews bulk tag changes | ROADMAP |
| TAG-03 | `kb-rag tags remove` deletes files from registry + Qdrant by payload filter | ROADMAP |
| TAG-04 | `kb-rag tags reingest` sets status to pending and deletes Qdrant chunks | ROADMAP |
| TAG-05 | Web UI `/admin/tags` shows filterable table with checkboxes and bulk actions toolbar | ROADMAP |

## Success Criteria

1. `kb-rag tags list` shows tag counts for Product, Type, Version, Status
2. `kb-rag tags update --dry-run` previews bulk changes without side effects
3. `kb-rag tags remove` deletes files from registry + Qdrant by payload filter
4. `kb-rag tags reingest` sets status to pending and deletes Qdrant chunks
5. Web UI `/admin/tags` shows filterable table with checkboxes and bulk actions toolbar
6. All destructive operations require confirmation; dry-run available everywhere
7. Inline tag editing works in `/admin/documents` browse table
8. Tag autocomplete suggests existing tags
9. Max 20 tags per document enforced
10. Tag deletion cascades to all documents

## Existing Patterns to Reuse

- **CLI**: `ingest/cli/reclassify.py` — bulk operations with Rich tables, filter expressions, --dry-run, --yes
- **Web UI**: `kb_server/ui/templates/admin/_documents_table.html` — checkbox + bulk toolbar pattern
- **Registry**: `ingest/core/metadata.py` — SQLite schema, bulk updates, status field ('pending', 'ok', 'error')
- **VectorStore**: `kb_server/vector_store.py` — `update_chunk_metadata()`, `delete_document()`
- **Auth**: `kb_server/auth/deps.py` — `require_admin` dependency for destructive ops
- **Jobs**: `ingest/core/metadata.py` — job tracking for background re-ingest

## Deferred Ideas (Future Phases)

- Tag search integration (opt-in via config toggle)
- Tag categories/groups (e.g., "Status" tags vs "Topic" tags)
- Tag color assignment
- Tag analytics (most used tags, untagged documents report)
- Tag-based access control

## Assumptions

- Qdrant payload can accept new `tags` field without schema migration (schemaless payload)
- Registry `status` field values: 'pending', 'ok', 'error' — used for re-ingest control
- File watcher detects `status=pending` and re-ingests on next scan interval
- Job queue infrastructure exists from Phase 28c
