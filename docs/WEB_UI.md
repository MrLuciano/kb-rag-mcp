# KB-RAG Web UI User Guide

## Overview

The KB-RAG Web UI provides a browser-based interface for:
- **Browsing** indexed documents with filtering and pagination
- **Testing** search queries with various parameters
- **Viewing** document details and metadata

Built with FastAPI, Bootstrap 5, and HTMX for a fast, lightweight experience.

## Quick Start

### Starting the UI Server

```bash
# Development
python3 server/ui/run_ui.py

# Production (systemd)
sudo systemctl start kb-rag-ui
sudo systemctl enable kb-rag-ui
```

### Accessing the UI

Default URL: http://localhost:8001

- **Browse Documents**: `/ui/browse`
- **Search Tester**: `/ui/search`
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

Service file: `deployment/systemd/kb-rag-ui.service`

```bash
# Install
sudo cp deployment/systemd/kb-rag-ui.service /etc/systemd/system/
sudo systemctl daemon-reload

# Manage
sudo systemctl start kb-rag-ui
sudo systemctl stop kb-rag-ui
sudo systemctl status kb-rag-ui
sudo systemctl enable kb-rag-ui  # Start on boot

# Logs
sudo journalctl -u kb-rag-ui -f
```

## Architecture

### Technology Stack

- **Backend**: FastAPI (async Python web framework)
- **Templating**: Jinja2
- **Frontend**: Bootstrap 5 + HTMX
- **Server**: Uvicorn (ASGI server)

### File Structure

```
server/ui/
├── __init__.py           # Package init
├── app.py                # FastAPI app initialization
├── routes.py             # Route handlers
├── run_ui.py             # Startup script
└── templates/
    ├── base.html         # Base template
    ├── browse.html       # Document browser
    ├── search.html       # Search tester
    ├── document.html     # Document detail
    └── error.html        # Error page
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
sudo journalctl -u kb-rag-ui -n 50
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
sudo systemctl status kb-rag-ui
```

**Verify routes loaded:**
```bash
curl http://localhost:8001/health
# Should return: {"status": "ok", "service": "kb-rag-ui"}
```

## Security Notes

- **No Authentication**: UI is designed for internal use only
- **Network Access**: Bind to 127.0.0.1 for local-only access
- **Reverse Proxy**: Use nginx/Apache for HTTPS in production
- **Database**: Read-only access (no write operations from UI)

## Performance

- **Pagination**: 20 docs/page prevents large result sets
- **Lightweight**: No JavaScript frameworks, minimal client-side code
- **Fast**: HTMX for dynamic updates without full page reloads
- **Efficient**: Direct SQLite queries with indexes

## Implemented Enhancements

The following features previously listed as future work are now implemented:

- ✅ **Query logging analytics dashboard** — `/ui/admin/query-analytics` with charts, top queries, slow queries, zero-result analysis (Phase 42)
- ✅ **Chunk preview with accordion** — Document detail page shows expandable chunk previews with keyword highlighting (Phase 43)
- ✅ **Real-time search integration** — The search tester now integrates with the MCP server via the Streamable HTTP transport (Phase 28c)

## Related Documentation

- [QUERY_ANALYSIS.md](QUERY_ANALYSIS.md) - Query logging guide
- [PHASE14_PLAN.md](PHASE14_PLAN.md) - Implementation details
- [OPERATIONS.md](OPERATIONS.md) - Deployment guide

## Support

For issues or questions:
- Check logs: `sudo journalctl -u kb-rag-ui -f`
- Verify config: `systemctl show kb-rag-ui`
- Review plan: `docs/PHASE14_PLAN.md`
