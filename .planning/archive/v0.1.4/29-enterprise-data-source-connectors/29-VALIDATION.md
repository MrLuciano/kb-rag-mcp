---
phase: 29
slug: enterprise-data-source-connectors
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-01
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]`) |
| **Quick run command** | `.venv/bin/pytest tests/test_confluence_connector.py tests/test_jira_connector.py tests/test_git_connector.py tests/test_connectors_base.py tests/test_connectors_staging.py tests/test_ingest_registry.py -x --tb=short -q` |
| **Full suite command** | `.venv/bin/pytest tests/ -x --tb=short -q` |
| **Estimated runtime** | ~37 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 37 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Requirement | Test Type | Automated Command | Status |
|---------|------|-------------|-----------|-------------------|--------|
| 29-01-T1 | 01 | Connector-aware MetadataStore schema (connector_state, sync checkpoint, etag, external_id) | unit | `pytest tests/test_ingest_registry.py::TestConnectorState -v` | ✅ green |
| 29-01-T1 | 01 | Schema migration v2→v3 preserves existing data | integration | `pytest tests/test_ingest_registry.py::TestConnectorState::test_connector_state_migration_from_v2 -v` | ✅ green |
| 29-01-T1 | 01 | Connector-state does not break local file registry | integration | `pytest tests/test_ingest_registry.py::TestConnectorState::test_connector_schema_does_not_break_local_registry -v` | ✅ green |
| 29-01-T2 | 01 | ConnectorBase ABC with abstract methods | unit | `pytest tests/test_connectors_base.py -v` | ✅ green |
| 29-01-T2 | 01 | RemoteDocument / SyncResult / ConnectorConfig models | unit | `pytest tests/test_connectors_base.py -v` | ✅ green |
| 29-01-T2 | 01 | Factory register/create/list | unit | `pytest tests/test_connectors_base.py -v` | ✅ green |
| 29-01-T2 | 01 | Staging helpers (single, batch, cleanup, metadata resolution) | unit | `pytest tests/test_connectors_staging.py -v` | ✅ green |
| 29-01-T3 | 01 | Connector CLI commands (list, stage) | smoke | `pytest tests/test_cli.py::TestConnectorCommands -v` | ✅ green |
| 29-01-T3 | 01 | CLI lists builtin connector types (confluence, jira, git) | smoke | `pytest tests/test_cli.py::TestConnectorCommands::test_connectors_list_shows_builtin_types -v` | ✅ green |
| 29-01-T3 | 01 | run_ingest works with legacy-only args (backward compat) | integration | `pytest tests/test_connectors_staging.py::TestStagedDocumentIngestPipeline::test_run_ingest_works_without_connector_params -v` | ✅ green |
| 29-01-T3 | 01 | Staged document → ingest pipeline end-to-end | integration | `pytest tests/test_connectors_staging.py::TestStagedDocumentIngestPipeline::test_staged_document_flows_into_ingest -v` | ✅ green |
| 29-01-T3 | 01 | Job system coexists with connector_state | integration | `pytest tests/test_job_system.py::TestConnectorAwareJobs::test_job_creation_with_connector_state_present -v` | ✅ green |
| 29-01-T3 | 01 | Worker processes connector-staged files | unit | `pytest tests/test_worker_system.py::test_worker_processes_staged_connector_file -v` | ✅ green |
| 29-02-T1 | 02 | Confluence auth headers (Basic/Bearer) | unit | `pytest tests/test_confluence_connector.py::TestConfluenceAuthHeaders -v` | ✅ green |
| 29-02-T1 | 02 | Storage→Markdown conversion (various content types) | unit | `pytest tests/test_confluence_connector.py::TestConfluenceContentExtraction -v` | ✅ green |
| 29-02-T1 | 02 | Pagination (offset/cursor URLs) | unit | `pytest tests/test_confluence_connector.py::TestConfluencePagination -v` | ✅ green |
| 29-02-T1 | 02 | CQL building (no checkpoint, with checkpoint, with labels) | unit | `pytest tests/test_confluence_connector.py::TestConfluenceCQL -v` | ✅ green |
| 29-02-T1 | 02 | Version detection (server vs cloud) | unit | `pytest tests/test_confluence_connector.py::TestConfluenceVersionDetection -v` | ✅ green |
| 29-02-T1 | 02 | fetch_documents (success, failure) | unit | `pytest tests/test_confluence_connector.py::TestConfluenceFetchDocuments -v` | ✅ green |
| 29-02-T1 | 02 | fetch_document (found, 404) | unit | `pytest tests/test_confluence_connector.py::TestConfluenceFetchDocuments::test_fetch_document_by_id -v` | ✅ green |
| 29-02-T1 | 02 | Rate limiting applied during fetch | unit | `pytest tests/test_confluence_connector.py::TestConfluenceFetchDocuments::test_fetch_applies_rate_limiting -v` | ✅ green |
| 29-02-T1 | 02 | Incremental checkpoint wiring (CQL lastModified) | unit | `pytest tests/test_confluence_connector.py::TestConfluenceFetchDocuments::test_fetch_incremental_uses_checkpoint -v` | ✅ green |
| 29-02-T1 | 02 | HTML fallback strips all tags | unit | `pytest tests/test_confluence_connector.py::TestConfluenceContentExtraction::test_html_fallback_strips_all_tags -v` | ✅ green |
| 29-03-T1 | 03 | JIRA auth headers (Basic/Bearer) | unit | `pytest tests/test_jira_connector.py::TestJiraAuthHeaders -v` | ✅ green |
| 29-03-T1 | 03 | JQL building (project, updated, filter) | unit | `pytest tests/test_jira_connector.py::TestJiraJQL -v` | ✅ green |
| 29-03-T1 | 03 | Pagination (startAt/maxResults) | unit | `pytest tests/test_jira_connector.py::TestJiraFetchDocuments::test_search_url_with_offset -v` | ✅ green |
| 29-03-T1 | 03 | Version detection (server vs cloud) | unit | `pytest tests/test_jira_connector.py::TestJiraVersionDetection -v` | ✅ green |
| 29-03-T1 | 03 | Issue parsing (with/without description) | unit | `pytest tests/test_jira_connector.py::TestJiraIssueParsing -v` | ✅ green |
| 29-03-T1 | 03 | fetch_documents (success, failure) | unit | `pytest tests/test_jira_connector.py::TestJiraFetchDocuments -v` | ✅ green |
| 29-03-T1 | 03 | fetch_document (found, 404) | unit | `pytest tests/test_jira_connector.py::TestJiraFetchDocuments::test_fetch_document_by_key -v` | ✅ green |
| 29-03-T1 | 03 | Rate limiting applied during fetch | unit | `pytest tests/test_jira_connector.py::TestJiraFetchDocuments::test_fetch_applies_rate_limiting -v` | ✅ green |
| 29-03-T1 | 03 | Incremental checkpoint wiring (JQL updated) | unit | `pytest tests/test_jira_connector.py::TestJiraFetchDocuments::test_fetch_incremental_uses_checkpoint -v` | ✅ green |
| 29-04-T1 | 04 | Git availability check | unit | `pytest tests/test_git_connector.py::TestGitConnect -v` | ✅ green |
| 29-04-T1 | 04 | File discovery (HEAD, specific commit) | unit | `pytest tests/test_git_connector.py::TestGitFileDiscovery -v` | ✅ green |
| 29-04-T1 | 04 | Diff-based change detection | unit | `pytest tests/test_git_connector.py::TestGitDiff -v` | ✅ green |
| 29-04-T1 | 04 | File content reading (HEAD, commit, removed) | unit | `pytest tests/test_git_connector.py::TestGitFileContent -v` | ✅ green |
| 29-04-T1 | 04 | Document parsing (md, py, yaml, unsupported) | unit | `pytest tests/test_git_connector.py::TestGitParseDocument -v` | ✅ green |
| 29-04-T1 | 04 | fetch_documents (no checkpoint, with checkpoint, failure) | unit | `pytest tests/test_git_connector.py::TestGitFetchDocuments -v` | ✅ green |
| 29-04-T1 | 04 | fetch_document (found, not found) | unit | `pytest tests/test_git_connector.py::TestGitFetchDocuments -v` | ✅ green |
| 29-04-T1 | 04 | Content type detection (11+ extensions) | unit | `pytest tests/test_git_connector.py::TestGitContentTypeMapping -v` | ✅ green |
| 29-04-T1 | 04 | Checkpoint from HEAD SHA | unit | `pytest tests/test_git_connector.py::TestGitCheckpoint -v` | ✅ green |
| 29-04-T1 | 04 | SSH auth sets correct env vars | unit | `pytest tests/test_git_connector.py::TestGitSSHAuth::test_ssh_auth_sets_env -v` | ✅ green |
| 29-04-T1 | 04 | Workspace cleanup on close | unit | `pytest tests/test_git_connector.py::TestGitWorkspaceCleanup::test_close_cleans_up_temp_workspace -v` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — no Wave 0 setup needed.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Audit 2026-07-01

| Metric | Count |
|--------|-------|
| Gaps found | 14 |
| Resolved | 14 |
| Escalated | 0 |

---

## Validation Sign-Off

- ✅ All tasks have automated verification
- ✅ Sampling continuity: no 3 consecutive tasks without automated verify
- ✅ Wave 0 not needed — existing infra covers all requirements
- ✅ No watch-mode flags
- ✅ Feedback latency < 37s
- ✅ `nyquist_compliant: true` set in frontmatter

**Approval:** pending
