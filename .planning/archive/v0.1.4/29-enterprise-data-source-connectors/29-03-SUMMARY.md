# Phase 29-03 SUMMARY: JIRA Connector

**Date:** 2026-06-10
**Type:** execute
**Status:** Complete

## Changes Made

### `ingest/connectors/jira.py` — JIRA connector (new, ~280 lines)
- `JiraConnector(ConnectorBase)` — supports JIRA Cloud and Data Center/Server
- **Auth:** Basic (Server) or Bearer (Cloud) from `JIRA_USERNAME`/`JIRA_TOKEN` env vars
- **JQL builder:** Project, `updated` (incremental sync), and custom JQL filter clauses
- **Pagination:** `startAt`/`maxResults` with `total` (works for both Cloud and DC)
- **Content extraction:** ADF (Atlassian Document Format) recursive text extraction to Markdown
- **Project iteration:** Lists projects, then fetches issues per project
- **Single issue fetch:** `fetch_document(issue_key)` with 404 handling
- **Rate limiting:** Via `MultiRateLimiter` (configurable via `JIRA_RATE_LIMIT`)
- **Factory registration:** Auto-registers as `"jira"` on import

### `tests/test_jira_connector.py` — 16 tests
- Auth header construction (Server + Cloud)
- JQL building (project, checkpoint, filter)
- Search URL with offset pagination
- Issue parsing (with ADF description, without description)
- Mocked fetch_documents, error handling, single document fetch, 404
- Factory registration verification

## Verification

| Suite | Result |
|---|---|
| `test_jira_connector.py` | 16/16 passed |
| Full suite | 871 passed, 2 pre-existing failures |

## Registered Connectors

```bash
kb-rag connectors list
# → confluence, jira
```
