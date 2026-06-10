# Confluence Connector Design

**Phase:** 29-02
**Date:** 2026-06-10
**Status:** Draft

## Overview

Single-file Confluence connector (`ingest/connectors/confluence.py`) that
implements `ConnectorBase` for both Confluence 7.9.3 Server/Data Center
and Confluence Cloud. Register with the factory for CLI discovery.

## Design Decisions

### Single file vs split
- **Decision:** Single file `confluence.py` (~300-350 lines)
- **Rationale:** All Confluence logic is tightly coupled — content API,
  pagination, auth, conversion. Splitting would create artificial boundaries
  without reuse.

### Auth configuration
- Env vars: `CONFLUENCE_URL`, `CONFLUENCE_USERNAME`, `CONFLUENCE_TOKEN`
- 7.9.3 (Server/DC): basic auth (`username:TOKEN` base64-encoded)
- Cloud: uses same token as bearer or OAuth (deferred to config)
- Version auto-detection: check endpoint for `/rest/api` vs `/wiki/rest/api`

### Pagination handling
- **7.9.3:** `start`/`limit` params (offset-based, max 200 `limit`)
- **Cloud:** cursor-based via `_links.next` in API response
- Extracted into `_paginate()` helper that yields (doc, next_cursor)

### Content conversion
- `html2text` — converts Storage Format (XHTML) to Markdown
- Falls back to `html.parser` stripping if `html2text` is not installed

### Incremental sync
- Checkpoint = ISO 8601 timestamp of last fetch
- CQL: `lastModified >= "2026-01-01 00:00"` appended when checkpoint exists
- Checkpoint stored in `connector_state` table via `MetadataStore`

### Rate limiting
- Reuses `MultiRateLimiter` from `ingest/worker/limiter.py`
- Confluence Cloud: 100 req/min; 7.9.3 Server: no strict limit (configurable)

## API

```
class ConfluenceConnector(ConnectorBase):
    async def connect(self) -> None
        # Validate credentials, test endpoint

    async def fetch_documents(self, since=None) -> SyncResult
        # Iterate spaces → CQL pages → fetch content
        # Build RemoteDocument list with title + content + metadata

    async def fetch_document(self, remote_id) -> RemoteDocument | None
        # GET /rest/api/content/{id}?expand=body.storage

    async def close(self) -> None
        # Close httpx client session

    def list_spaces(self) -> list[dict]
        # GET /rest/api/space, yields space keys + names
```

## Tests

- `tests/test_confluence_connector.py` — httpx mock-based tests
- Cover: pagination (offset + cursor), content conversion, CQL queries,
  error handling (429, 401, 404), auth header construction,
  incremental sync checkpoint flow

## Dependencies

- `html2text` (new, added to `requirements.in` / `requirements.txt`)
- `httpx` (existing)
