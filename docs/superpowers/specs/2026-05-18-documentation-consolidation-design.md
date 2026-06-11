# Documentation Consolidation Design

**Date:** 2026-05-18  
**Status:** Approved

## Problem

After 16 PHASEs + QA pipeline, documentation is scattered across 30+ files:
PHASE*_COMPLETION.md, PHASE*_PLAN.md, topic docs, and two stale index files
(PLAN.md roadmap progress and INDEX.md both stopped at PHASE 5). There is no
single place to understand the current state of the system.

## Goals

- One living reference doc for both developers and onboarders
- PLAN.md remains the authoritative roadmap
- INDEX.md remains the navigation entry point
- Historical PHASE lifecycle docs archived, not deleted
- Topic docs (SEARCH_QUALITY.md, OPERATIONS.md, etc.) remain in place

## Non-Goals

- Rewriting topic docs
- Changing code
- Translating content to PT-BR

## File Structure After

```
docs/
  REFERENCE.md          NEW — living ops+architecture reference
  PLAN.md               UPDATED — all 16 PHASEs + QA marked complete
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
    PHASE1_COMPLETION.md
    PHASE2_COMPLETION.md
    PHASE3_COMPLETION.md
    PHASE4_COMPLETION.md
    PHASE5_COMPLETION.md
    PHASE7_COMPLETION.md
    PHASE8_COMPLETION.md
    PHASE9_COMPLETION.md
    PHASE10_COMPLETION.md
    PHASE12_COMPLETION.md
    PHASE13_COMPLETION.md
    PHASE14_COMPLETION.md
    PHASE16_COMPLETION.md
    PHASE3_PLAN.md
    PHASE4_PLAN.md
    PHASE12_PLAN.md
    PHASE13_PLAN.md
    PHASE14_PLAN.md
    PHASE16_PLAN.md
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
8. **Roadmap Status** — compact table all 16 PHASEs + QA, links to PLAN.md
9. **Known Issues & Constraints** — sharp edges

## PLAN.md Updates

- Mark PHASEs 1–16 complete in the timeline section
- Add QA Pipeline as completed milestone
- Update "Priority Execution Order" — everything shipped, no pending phases

## INDEX.md Updates

- PHASE completion list: all 16 shown as complete
- Add REFERENCE.md under Getting Started as primary entry point
- Update statistics table: 252 tests, 16+QA phases complete
- Add archive/ link for historical docs
- Remove stale last-updated date
