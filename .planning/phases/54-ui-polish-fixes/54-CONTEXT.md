# Phase 54 — UI Polish Fixes

**Audit source:** UI-REVIEW.md (2026-06-16)
**Score baseline:** 17/24 overall; 18/24 after top-3 priority fixes in Phase 53
**Status:** Planned (4 plans, 13 sub-tasks)

## Scope

Resolve 12 unfixed findings from UI-REVIEW.md audit across copywriting, typography, layout, and UX pillars. All changes are limited to `kb_server/ui/templates/` — no backend, no tests, no docs changes.

## Plans

| Plan | Focus | Files | Tasks |
|------|-------|-------|-------|
| 54-01 | Copywriting Fixes | shell.html, tab_profile.html, search.html, document.html | 4 label/message changes |
| 54-02 | Heading Hierarchy & Typography | tab_profile.html, tab_analytics.html | 4 heading hierarchy fixes |
| 54-03 | Layout & Spacing | error.html, browse.html, _job_status.html, search.html | 4 layout fixes |
| 54-04 | UX Feature Additions | base.html, tab_ragas.html, search_results.html | 3 new interactive features |

## Unfixed Findings (from UI-REVIEW.md)

- "RAGAS Evaluation" jargon in sidebar → Plan 1
- Abbreviated labels "K"/"BM25"/"Rerank" → Plan 1
- "Search Tester" name → Plan 1
- "Chunk Loading Failed" message → Plan 1
- h4.h6 outline skip in profile → Plan 2
- h3.h5 headings in analytics → Plan 2
- Error page double container → Plan 3
- Pagination href whitespace → Plan 3
- Job status counters alignment → Plan 3
- Mobile search spacing → Plan 3
- Non-dismissible alerts → Plan 4
- RAGAS no progress indication → Plan 4
- Search results no pagination → Plan 4

## Previously Fixed (Phase 53)

- Login modal shown immediately on init (BLOCKER)
- Heading hierarchy on document.html
- Search highlighting and badge contrast
