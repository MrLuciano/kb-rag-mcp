---
status: testing
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
updated: 2026-06-11T03:35:00Z
---

## Current Test

number: 2
name: Confluence connector env vars
expected: |
  Env vars CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_TOKEN
  configure the Confluence connector
awaiting: user response

## Tests

### 1. Connector factory has 3 registered connectors
expected: Factory reports 3 connector types (confluence, jira, git) when listed
result: issue
reported: "command shows No connectors registered"
severity: major

### 2. Confluence connector env vars
expected: Env vars CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_TOKEN configure the Confluence connector
result: [pending]

### 3. JIRA connector env vars
expected: Env vars JIRA_URL, JIRA_USERNAME, JIRA_TOKEN configure the JIRA connector
result: [pending]

### 4. Git connector env vars
expected: ENV vars GIT_REPO_URL, GIT_REPO_PATH configure the Git connector; supports HTTPS token and SSH auth
result: [pending]

### 5. Knowledge graph MCP tools registered
expected: MCP reports 8 tools including get_related_documents and explore_topic
result: [pending]

### 6. MCP prompts registered
expected: MCP advertises extract_answer and summarize_documents prompts
result: [pending]

### 7. API key auth CLI
expected: `kb-rag auth create`, `auth list`, `auth revoke` commands exist and work
result: [pending]

### 8. API key auth secures SSE endpoint
expected: With AUTH_ENABLED=true, SSE endpoint returns 401 without valid Bearer token
result: [pending]

### 9. Rate limiting SSE endpoint
expected: With RATE_LIMIT_ENABLED=true, exceeding limits returns HTTP 429 with Retry-After header
result: [pending]

### 10. Rate limiting at tool call level
expected: With RATE_LIMIT_ENABLED=true in stdio transport, over-limit calls return error TextContent
result: [pending]

### 11. Upload quotas CLI
expected: `kb-rag quota show`, `quota set`, `quota reset` commands exist and work
result: [pending]

### 12. Upload quota enforcement
expected: Ingest with quotas configured rejects files exceeding limits before chunking/embedding
result: [pending]

### 13. Multi-KB search parameter
expected: search_kb tool accepts kb_ids parameter (array of strings) alongside existing parameters
result: [pending]

### 14. All tests pass
expected: `pytest --ignore=tests/test_cli_reclassify.py` shows 1000+ tests passing
result: [pending]

## Summary

total: 14
passed: 0
issues: 1
pending: 13
skipped: 0
blocked: 0

## Gaps

- truth: "Factory reports 3 connector types (confluence, jira, git) when listed"
  status: failed
  reason: "User reported: command shows No connectors registered"
  severity: major
  test: 1
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
