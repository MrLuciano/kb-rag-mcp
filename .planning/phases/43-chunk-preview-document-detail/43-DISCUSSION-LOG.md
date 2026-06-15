# Phase 43: Chunk Preview in Document Detail - Discussion Log

**Date:** 2026-06-15
**Phase:** 43-chunk-preview-document-detail
**Areas discussed:** Display format, Highlighting, Integration, Metadata, Pagination

---

## Display Format

| Option | Description | Selected |
|--------|-------------|----------|
| Expandable accordion | Bootstrap accordion, collapsed by default | ✓ |
| Tabbed sections | Tabs for Chunks, Metadata, Raw Text | |
| Continuous scroll | Sequential rendered list | |

## Highlighting

| Option | Description | Selected |
|--------|-------------|----------|
| Server-side <mark> | Backend wraps matches, no JS | ✓ |
| Client-side JS | Alpine.js scans and marks text | |
| No highlighting | Raw text only | |

## Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Add to existing route | Enhance /ui/document/{id} | ✓ |
| HTMX partial | New /ui/document/{id}/chunks endpoint | |
| SPA tab | Admin SPA tab for chunk view | |

## Metadata

| Option | Description | Selected |
|--------|-------------|----------|
| Text only | Chunk content, no scores | ✓ |
| Text + score + sequence | Chunk index + relevance | |
| Full metadata | Score, count, tokens | |

## Pagination

| Option | Description | Selected |
|--------|-------------|----------|
| First 10 + Show More | 10 expanded, remaining collapsed, HTMX button | ✓ |
| All collapsed | All accordion items collapsed | |
| Paginated 20/page | Next/prev navigation | |

## the agent's Discretion

- Qdrant scroll query details
- Exact highlighting implementation
- VectorStore method for chunk retrieval

## Deferred Ideas

- Score/vector distance display
- Full metadata view
- Separate chunk detail page
- Client-side highlighting
