# Documentation Consolidation Design

**Date:** 2026-05-18  
**Status:** Approved

## Problem

After 16 FASEs + QA pipeline, documentation is scattered across 30+ files:
FASE*_COMPLETION.md, FASE*_PLAN.md, topic docs, and two stale index files
(PLAN.md roadmap progress and INDEX.md both stopped at FASE 5). There is no
single place to understand the current state of the system.

## Goals

- One living reference doc for both developers and onboarders
- PLAN.md remains the authoritative roadmap
- INDEX.md remains the navigation entry point
- Historical FASE lifecycle docs archived, not deleted
- Topic docs (SEARCH_QUALITY.md, OPERATIONS.md, etc.) remain in place

## Non-Goals

- Rewriting topic docs
- Changing code
- Translating content to PT-BR

## File Structure After

```
docs/
  REFERENCE.md          NEW — living ops+architecture reference
  PLAN.md               UPDATED — all 16 FASEs + QA marked complete
  INDEX.md              UPDATED — links REFERENCE.md, correct counts
  TESTING.md            unchanged
  INSTRUCTIONS.md       unchanged
  INSTRUCTIONS.pt-BR.md unchanged
  SEARCH_QUALITY.md     unchanged
  AUTO_INGESTION.md     unchanged
  OPERATIONS.md         unchanged
  TROUBLESHOOTING.md    unchanged
  RAG_EVALUATION.md     unchanged
  QUERY_ANALYSIS.md     unchanged
  WEB_UI.md             unchanged
  VERSION_FILTERING.md  unchanged
  METADATA_OVERRIDES.md unchanged
  archive/
    FASE1_COMPLETION.md
    FASE2_COMPLETION.md
    FASE3_COMPLETION.md
    FASE4_COMPLETION.md
    FASE5_COMPLETION.md
    FASE7_COMPLETION.md
    FASE8_COMPLETION.md
    FASE9_COMPLETION.md
    FASE10_COMPLETION.md
    FASE12_COMPLETION.md
    FASE13_COMPLETION.md
    FASE14_COMPLETION.md
    FASE16_COMPLETION.md
    FASE3_PLAN.md
    FASE4_PLAN.md
    FASE12_PLAN.md
    FASE13_PLAN.md
    FASE14_PLAN.md
    FASE16_PLAN.md
    HYGIENE_STATUS.md
```

## REFERENCE.md Sections

1. **What This Is** — 2-paragraph system description
2. **Architecture** — ASCII component diagram, data flow
3. **Component Map** — table: component | package | key files | purpose
4. **Configuration** — all env vars in one table
5. **Running the System** — prerequisites, start services, ingest, MCP server, QA pipeline
6. **QA Results** — current OTCS results, how to re-run
7. **Test Suite** — how to run, coverage, key files
8. **Roadmap Status** — compact table all 16 FASEs + QA, links to PLAN.md
9. **Known Issues & Constraints** — sharp edges

## PLAN.md Updates

- Mark FASEs 1–16 complete in the timeline section
- Add QA Pipeline as completed milestone
- Update "Priority Execution Order" — everything shipped, no pending phases

## INDEX.md Updates

- FASE completion list: all 16 shown as complete
- Add REFERENCE.md under Getting Started as primary entry point
- Update statistics table: 252 tests, 16+QA phases complete
- Add archive/ link for historical docs
- Remove stale last-updated date
