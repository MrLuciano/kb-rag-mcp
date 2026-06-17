# Phase 51 — Discussion Log

**Date:** 2026-06-17  
**Participants:** User + Agent  
**Areas Discussed:** 12  
**Decisions Captured:** 13

---

## Area 1: Tag Scope
**Question:** Document-level or chunk-level tags?  
**Options:** Document-level (all chunks share) / Chunk-level (per-chunk) / Hybrid  
**Decision:** Document-level — all chunks of a document share the same tags. Simpler mental model for admins.

## Area 2: Tag vs Classification
**Question:** How should tags relate to auto-classified fields in UI/CLI?  
**Options:** Visually separate / Mixed together  
**Decision:** Visually separate — dedicated tags column/badges, distinct from product/type/version/etc.

## Area 3: Tag Format
**Question:** What validation rules for tag strings?  
**Options:** Minimal (max 50, no whitespace, case-sensitive) / Strict (lowercase, alphanumeric + hyphen, max 30) / None  
**Decision:** Minimal validation — max 50 chars, no whitespace, case-insensitive (stored lowercase).

## Area 4: UI Placement
**Question:** Where should tag management live in Admin SPA?  
**Options:** Integrated in /admin/documents / Separate /admin/tags tab / Both  
**Decision:** Both — inline editing in /admin/documents + dedicated /admin/tags for bulk/cleanup.

## Area 5: Re-ingest Trigger
**Question:** What happens when admin clicks "Re-ingest"?  
**Options:** Mark pending for watcher / Immediate synchronous / Queue as background job  
**Decision:** Queue as background job, show progress in Jobs tab. Non-blocking.

## Area 6: Tag Search
**Question:** How should tags interact with search system?  
**Options:** Searchable / Browse-only / Opt-in searchable  
**Decision:** Opt-in searchable — stored in Qdrant payload, not indexed until explicitly enabled via config.

## Area 7: Audit Log
**Question:** What detail level for tag mutation audit log?  
**Options:** Minimal / Detailed (before/after snapshot) / Bulk-optimized  
**Decision:** Minimal — user ID, timestamp, document path, action, tag values.

## Area 8: Migration
**Question:** How to handle existing documents without tags?  
**Options:** Lazy (add on first edit) / Eager (bulk migration script) / Hybrid  
**Decision:** Lazy migration — no bulk script. Tags field added on first edit.

## Area 9: Error Handling
**Question:** How to handle partial failures in bulk operations?  
**Options:** All-or-nothing / Best-effort / Per-document confirmation  
**Decision:** Best-effort — apply successes, report failures in summary.

## Area 10: Tag Visuals
**Question:** How should tags look in the UI?  
**Options:** Plain badges / Auto-colored / User-assigned colors  
**Decision:** Plain Bootstrap badges — consistent, no color management.

## Area 11: Tag Limits
**Question:** Max tags per document?  
**Options:** Max 10 / Max 20 / No limit  
**Decision:** Max 20 tags per document, enforced at API level.

## Area 12: Tag Autocomplete
**Question:** Should tag input suggest existing tags?  
**Options:** Yes / No  
**Decision:** Yes — dropdown with existing tags as you type.

## Area 13: Tag Deletion
**Question:** What happens when a tag is deleted from the system?  
**Options:** Remove from all docs / Orphan / Prevent if in use  
**Decision:** Cascade — deleting a tag removes it from all documents.

---

## Deferred Ideas

- Tag search integration (opt-in via config toggle) — future phase
- Tag categories/groups — future phase
- Tag color assignment — future phase
- Tag analytics (usage reports) — future phase
- Tag-based access control — future phase

## Key Insight from User

> "The operations defined for the tags must be available for the classification first. Tags are complementary to the internal classifications to provide flexibility."

This guided the decision to keep tags visually separate from auto-classified fields and to ensure tags don't replace but complement the existing taxonomy.
