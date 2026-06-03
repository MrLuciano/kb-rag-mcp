# Phase 29: Enterprise Data Source Connectors

**Status:** Backlog (promoted from ROADMAP.md)
**Priority:** High
**Code:** ENT-01
**Competitive Reference:** [qdrant-loader](https://github.com/martin-papy/qdrant-loader) (v0.6.2) — enterprise connectors
**Promoted from:** `.planning/ROADMAP.md` Backlog (High Priority)

## Objective

Add ingest connectors for enterprise data sources: Confluence (Cloud + Data Center), JIRA (Cloud + Data Center), and Git repositories. Enables teams whose content already lives in these systems to index it into kb-rag-mcp without manual export.

## Expected Deliverables

- Connector architecture (base class + concrete implementations)
- Confluence connector (Cloud + Data Center variants)
- JIRA connector (Cloud + Data Center variants)
- Git repository connector (clone + diff-based incremental sync)
- Auth handling (API keys, OAuth tokens, SSH keys)
- Incremental sync support (change detection, delta updates)
- CLI integration (`kb-ingest --source confluence|jira|git`)

## Key Design Decisions to Research

- **Connector base class:** Define interface for all connectors (`ConnectorBase` with `connect()`, `fetch_documents()`, `get_changes(since)`, `close()`)
- **Auth abstraction:** Handle multiple auth methods (API tokens, OAuth, SSH keys) per data source type
- **Change detection:** How to track incremental changes (Confluence content history, JIRA issue updated, Git push events)
- **Rate limiting:** Respect API rate limits on Confluence/JIRA (exponential backoff, scheduled polling)
- **Data mapping:** Map Confluence pages, JIRA issues, Git repos to `IngestDocument` format

## Implementation Scope

### Confluence Connector
- Fetch pages, attachments, comments via Confluence REST API
- Space-level and page-level ingestion
- Convert Confluence wiki markup to plain text
- Handle content_history for incremental updates

### JIRA Connector
- Fetch issues, comments, attachments via JIRA REST API
- Project-level and filter-based ingestion
- Map JIRA fields to document metadata (priority, status, assignee, labels)

### Git Connector
- Clone repositories and track file changes
- Incremental sync via git diff / history analysis
- Markdown and code file extraction
- Option to restrict to specific branches / paths

## Open Questions

1. Should connectors run as part of the ingest pipeline or as separate services?
2. How to handle large Confluence spaces (1000+ pages) without timing out?
3. Should we support Webhook-based real-time sync or just polling?

## See Also

- `qdrant-loader` architecture (GitHub: martin-papy/qdrant-loader)
- `ingest/ingest.py` — existing ingest pipeline
- `ingest/registry.py` — file tracking and dedup