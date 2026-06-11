---
status: complete
phase: 35-multi-kb-aggregated-search
source:
  - 29-enterprise-data-source-connectors
  - 30-cross-doc-knowledge-graph
  - 31-mcp-prompt-templates
  - 32-api-key-authentication
  - 33-request-rate-limiting
  - 34-upload-index-quotas
  - 35-multi-kb-aggregated-search
started: 2026-06-11T03:30:00Z
updated: 2026-06-11T03:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Connector factory has 3 registered connectors
expected: Factory reports 3 connector types (confluence, jira, git) when listed
result: issue
reported: "command shows No connectors registered"
severity: major

### 2. Confluence connector env vars
expected: Env vars CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_TOKEN configure the Confluence connector
result: blocked
blocked_by: prior-phase
reason: "Connectors not registered — same root cause as Test 1"

### 3. JIRA connector env vars
expected: Env vars JIRA_URL, JIRA_USERNAME, JIRA_TOKEN configure the JIRA connector
result: blocked
blocked_by: prior-phase
reason: "Connectors not registered — same root cause as Test 1"

### 4. Git connector env vars
expected: ENV vars GIT_REPO_URL, GIT_REPO_PATH configure the Git connector; supports HTTPS token and SSH auth
result: blocked
blocked_by: prior-phase
reason: "Connectors not registered — same root cause as Test 1"

### 5. Knowledge graph MCP tools registered
expected: MCP reports 8 tools including get_related_documents and explore_topic
result: pass
notes: "8 tool handlers verified in code: _search_kb, _list_documents, _get_chunk, _kb_stats, _list_collections, _list_filter_options, _get_related_documents, _explore_topic. Tests validate tool registration and dispatch."

### 6. MCP prompts registered
expected: MCP advertises extract_answer and summarize_documents prompts
result: pass
notes: "PROMPT_DEFINITIONS in kb_server/prompts.py contains extract_answer and summarize_documents. 15 test_server_prompts tests pass."

### 7. API key auth CLI
expected: `kb-rag auth create`, `auth list`, `auth revoke` commands exist and work
result: pass
notes: "`python -m ingest.cli.main auth --help` shows create, list, revoke commands. 21 test_auth_registry tests pass."

### 8. API key auth secures SSE endpoint
expected: With AUTH_ENABLED=true, SSE endpoint returns 401 without valid Bearer token
result: blocked
blocked_by: server
reason: "Requires running MCP server with Qdrant which is not available locally"

### 9. Rate limiting SSE endpoint
expected: With RATE_LIMIT_ENABLED=true, exceeding limits returns HTTP 429 with Retry-After header
result: blocked
blocked_by: server
reason: "Requires running MCP server with Qdrant which is not available locally"

### 10. Rate limiting at tool call level
expected: With RATE_LIMIT_ENABLED=true in stdio transport, over-limit calls return error TextContent
result: blocked
blocked_by: server
reason: "Requires running MCP server with Qdrant which is not available locally"

### 11. Upload quotas CLI
expected: `kb-rag quota show`, `quota set`, `quota reset` commands exist and work
result: pass
notes: "`python -m ingest.cli.main quota --help` shows set, show, reset commands. 21 test_quotas tests pass."

### 12. Upload quota enforcement
expected: Ingest with quotas configured rejects files exceeding limits before chunking/embedding
result: pass
notes: "check_quota() logic verified via unit tests. Quota enforcement in run_ingest() before processing loop per code inspection."

### 13. Multi-KB search parameter
expected: search_kb tool accepts kb_ids parameter (array of strings) alongside existing parameters
result: pass
notes: "kb_ids parameter implemented in _search_kb handler in server.py. CollectionRouter.resolve_multi(), VectorStore.multi_search(), merge_multi_collection_results() all tested. 23 test_server_tools tests for kb_ids path pass."

### 14. All tests pass
expected: `pytest --ignore=tests/test_cli_reclassify.py` shows 1000+ tests passing
result: pass
notes: "1061 passed, 12 skipped, 0 failures (ignoring 2 pre-existing Qdrant-dependent failures in test_cli_reclassify.py)"

## Summary

total: 14
passed: 8
issues: 1
pending: 0
skipped: 0
blocked: 5

## Gaps

- truth: "Factory reports 3 connector types (confluence, jira, git) when listed"
  status: failed
  reason: "User reported: command shows No connectors registered"
  severity: major
  test: 1
  root_cause: "connector modules (confluence, jira, git) call factory.register() at module level, but no code eagerly imports them. ingest/connectors/__init__.py is empty — does not import submodules. CLI's list_connectors and tests only see the registry after an explicit import triggers the side-effect."
  artifacts:
    - path: "ingest/connectors/__init__.py"
      issue: "Empty __init__.py does not eagerly import connector submodules"
    - path: "ingest/cli/connectors.py"
      issue: "list_connectors does not import connector modules before checking registry"
  missing:
    - "Add 'from ingest.connectors import confluence, jira, git' to ingest/connectors/__init__.py"
  debug_session: ""
