# KB-RAG Web UI User Guide

## Overview

The KB-RAG Web UI provides a browser-based interface for:
- **Browsing** indexed documents with filtering and pagination
- **Testing** search queries with various parameters
- **Viewing** document details and metadata

Built with FastAPI, Bootstrap 5, Alpine.js + HTMX for a fast, lightweight experience.

## Quick Start

The Admin SPA is served by the main MCP server — no separate UI server needed.

### Starting the Server

```bash
# Development (serves both MCP + Admin UI)
python -m kb_server.server

# Production
sudo systemctl start kb-rag-mcp
```

### Accessing the UI

Default URL: http://localhost:8001

- **Browse Documents**: `/ui/browse`
- **Search Tester**: `/ui/search`
- **Admin SPA**: `/admin/` (requires auth if `AUTH_ENABLED=true`)
- **Health Check**: `/health`

## Features

### 1. Document Browser (`/ui/browse`)

Browse all indexed documents with:

**Filters:**
- Product (e.g., "AppServer", "DataSync")
- Document Type (e.g., "install_guide", "api_guide")
- Version (e.g., "23.4", "1.0.0")
- Status (completed, failed, pending)

**Display:**
- Source filename
- Product, type, version
- Status with color coding (green=completed, red=failed)
- Chunk count
- Click any document to view details

**Pagination:**
- 20 documents per page
- Smart pagination (shows first/last + current +/- 1)

### 2. Search Tester (`/ui/search`)

Test search queries with:

**Parameters:**
- Query text (required)
- Top K (1-20, default 5)
- Product filter (optional)
- Version filter (optional)
- Hybrid search toggle (dense + BM25)
- Cross-encoder reranking toggle

**Note:** Search functionality requires MCP server integration. 
Current version shows a UI mockup.

### 3. Document Detail (`/ui/document/{id}`)

View comprehensive document metadata:
- ID, status, file type
- Product, document type, version
- Chunk count (how many searchable chunks)
- SHA256 hash
- Status alerts (failed, no chunks, success)

### 4. Admin SPA (`/admin/`)

The Admin SPA provides an integrated management panel with:

**Tabs:**
- **Documents** — Browse, filter, paginate, bulk select documents with checkboxes and export
- **Ingestion** — Monitor ingest status, manage ingestion schedules (CRON), view schedule status
- **RAGAS** — RAG evaluation pipeline controls and results display
- **Admin** — Server configuration (config editor with HTMX PUT save + Reset All), session management (list/revoke), credential management (generate/revoke API keys)

**Features:**
- Login overlay with API key authentication (Alpine.js)
- Responsive hamburger sidebar (280px expanded / icon-only collapsed)
- Monitor lights panel showing health components with latency
- CSP nonce on inline scripts for security
- Auth router mounted on UI app

## Configuration

### Environment Variables

```bash
# Server configuration
UI_HOST=0.0.0.0          # Listen address
UI_PORT=8001             # Listen port (default 8001)

# Database path
KB_METADATA_DB=data/kb_metadata.db  # Path to metadata database
```

### systemd Service

The Admin SPA is served by the main MCP server — the legacy `kb-rag-ui` systemd service is no longer used.

Service file: `deployment/systemd/kb-rag-mcp.service`

```bash
# Install
sudo cp deployment/systemd/kb-rag-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload

# Manage
sudo systemctl start kb-rag-mcp
sudo systemctl stop kb-rag-mcp
sudo systemctl status kb-rag-mcp
sudo systemctl enable kb-rag-mcp  # Start on boot

# Logs
sudo journalctl -u kb-rag-mcp -f
```

## Architecture

### Technology Stack

- **Backend**: FastAPI (async Python web framework)
- **Templating**: Jinja2 with Alpine.js + HTMX for interactivity
- **Frontend**: Bootstrap 5 (legacy), Alpine.js + HTMX (Admin SPA)
- **CSP**: Content Security Policy with nonces on inline scripts
- **Server**: Uvicorn (ASGI server, shared with MCP)

### File Structure

```
kb_server/ui/
├── __init__.py           # Package init
├── app.py                # FastAPI app initialization (mounted on main server)
├── routes.py             # Legacy route handlers (/ui/browse, /ui/search, ...)
├── routes_admin.py       # Admin SPA routes (/admin/, /admin/tabs/*)
├── run_ui.py             # Standalone startup (dev only)
├── static/
│   └── styles.css        # UI stylesheet
└── templates/
    ├── base.html         # Legacy base template
    ├── browse.html       # Legacy document browser
    ├── search.html       # Legacy search tester
    ├── document.html     # Legacy document detail
    ├── document_chunks.html
    ├── error.html        # Error page
    ├── search_results.html
    └── admin/            # Admin SPA templates (Alpine.js)
        ├── shell.html
        ├── tab_documents.html
        ├── tab_ingestion.html
        ├── tab_ragas.html
        ├── tab_admin.html
        ├── tab_monitoring.html
        ├── tab_analytics.html
        ├── tab_tags.html
        ├── tab_users.html
        ├── tab_profile.html
        └── _*.html       # Partial templates (loaders, tables, editors)
```

### Database Schema

Queries the `files` table in `kb_metadata.db`:

```sql
SELECT * FROM files
WHERE product = ? 
  AND doc_type = ?
  AND version = ?
  AND status = ?
ORDER BY id DESC
LIMIT 20 OFFSET 0
```

## Usage Examples

### Browse All Documents

1. Navigate to http://localhost:8001/ui/browse
2. See all indexed documents (20 per page)
3. Use pagination to see more

### Filter by Product

1. Go to http://localhost:8001/ui/browse
2. Enter "AppServer" in Product field
3. Click Filter
4. See only AppServer documents

### View Document Details

1. Browse documents
2. Click any document filename or "View" button
3. See full metadata and status

### Test a Search Query

1. Navigate to http://localhost:8001/ui/search
2. Enter query: "How to install SSL?"
3. Set Top K: 5
4. Enable Hybrid Search
5. Click Search
6. (Note: Full integration requires MCP API endpoint)

## Troubleshooting

### UI Won't Start

**Check port availability:**
```bash
sudo lsof -i :8001
```

**Check database path:**
```bash
ls -l data/kb_metadata.db
```

**Check logs:**
```bash
sudo journalctl -u kb-rag-mcp -n 50
```

### No Documents Shown

**Verify database has data:**
```bash
sqlite3 data/kb_metadata.db "SELECT COUNT(*) FROM files;"
```

**Check database permissions:**
```bash
ls -l data/kb_metadata.db
# Should be readable by kb-rag user
```

### 404 Not Found

**Check service status:**
```bash
sudo systemctl status kb-rag-mcp
```

**Verify routes loaded:**
```bash
curl http://localhost:8001/health
# Should return: {"status": "ok", "service": "kb-rag-mcp"}
```

## Security Notes

- **Authentication**: Optional — set `AUTH_ENABLED=true` to enable login with API keys
- **Admin SPA**: The `/admin/` panel requires authentication when `AUTH_ENABLED=true`
- **Network Access**: Bind to `127.0.0.1` for local-only access
- **Reverse Proxy**: Use nginx/Apache for HTTPS in production
- **Database**: Read-only access (no write operations from legacy UI)

## Performance

- **Pagination**: 20 docs/page prevents large result sets
- **Lightweight**: Alpine.js + HTMX for minimal client-side overhead
- **Fast**: HTMX for dynamic updates without full page reloads
- **Efficient**: Direct SQLite queries with indexes

## Implemented Enhancements

The following features previously listed as future work are now implemented:

- ✅ **Admin SPA** — Full management panel with Documents, Ingestion, RAGAS, and Admin tabs (Phase 28c)
- ✅ **Query logging analytics dashboard** — `/ui/admin/query-analytics` with charts, top queries, slow queries, zero-result analysis (Phase 42)
- ✅ **Chunk preview with accordion** — Document detail page shows expandable chunk previews with keyword highlighting (Phase 43)
- ✅ **Real-time search integration** — The search tester now integrates with the MCP server via the Streamable HTTP transport (Phase 28c)

## Related Documentation

- [QUERY_ANALYSIS.md](QUERY_ANALYSIS.md) - Query logging guide
- [PHASE14_PLAN.md](PHASE14_PLAN.md) - Implementation details
- [OPERATIONS.md](OPERATIONS.md) - Deployment guide

## Support

For issues or questions:
- Check logs: `sudo journalctl -u kb-rag-mcp -f`
- Verify config: `systemctl show kb-rag-mcp`
- Review plan: `docs/PHASE14_PLAN.md`
