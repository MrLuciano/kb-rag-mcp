# Phase 34: Upload and Index Quotas

**Status:** Backlog (promoted from ROADMAP.md)
**Priority:** Medium
**Code:** QUOTA-01
**Competitive Reference:** [kalicyh/mcp-rag](https://github.com/kalicyh/mcp-rag) — upload/index quotas
**Promoted from:** `.planning/ROADMAP.md` Backlog (Medium Priority)

## Objective

Add configurable limits on how much can be uploaded/indexed: max files per upload, max bytes per upload, max bytes per file, max documents per index, max chunks per index, max characters per index.

## Expected Deliverables

- Quota enforcement at ingest time (fail fast before processing)
- Per-KB quotas stored in registry and configurable via CLI
- CLI commands to set, view, reset quotas per KB
- HTTP 413 response when upload exceeds size limit
- MCP tool: `set_quota`, `get_quota`, `reset_quota`
- Default quotas: unlimited (backward compatible)

## Quota Fields

| Field | Description | Default |
|-------|-------------|---------|
| `max_files_per_upload` | Max files in single ingest call | unlimited |
| `max_bytes_per_upload` | Max total bytes in single ingest call | unlimited |
| `max_bytes_per_file` | Max bytes per individual file | unlimited |
| `max_documents_per_index` | Max docs in a KB | unlimited |
| `max_chunks_per_index` | Max chunks in a KB | unlimited |
| `max_chars_per_index` | Max total text chars in a KB | unlimited |

## Key Design Decisions

- **Enforcement:** Fail at ingest start (before chunking/embedding) — avoids wasted computation
- **Tracking:** Store current usage in registry alongside quota limits
- **Error:** Return descriptive HTTP 413 or 400 with which quota was exceeded
- **Reset:** Admin can reset usage counters (e.g., after archiving old documents)

## Implementation Scope

1. Add quota fields to `knowledge_bases` table in registry
2. Add `quota_usage` table to track current counts (chars, chunks, docs)
3. Check quotas in `ingest/ingest.py` before processing
4. Return HTTP 413/400 with quota info when exceeded
5. CLI: `kb-ingest quota set --kb-id <id> --max-files 100 --max-chars 10000000`
6. MCP tools: `set_quota`, `get_quota`

## Open Questions

1. Should quotas apply per time period (monthly reset)?
2. Do we notify users before they hit quota (soft limit warning)?
3. Should cross-KB aggregation limits exist for MULTIKB-01?

## See Also

- `kalicyh/mcp-rag` quota implementation (GitHub: kalicyh/mcp-rag)
- `kb_server/kb_registry.py` — existing registry
- `ingest/ingest.py` — ingest pipeline