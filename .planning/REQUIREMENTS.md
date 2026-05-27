# Requirements: v1.3 Post-Ship Polish & Infrastructure

## Milestone Goal

Deliver capability negotiation, fix Grafana datasource, backfill process debt (VERIFICATION.md), resolve test environment issues, codebase hygiene sweep, and wire integration checker CI gate.

---

## Active Requirements

### Phase 17: Capability Negotiation

- [ ] **CAPNEG-01**: MCP server advertises classified attributes (vendor, product, subsystem, version) during tool negotiation — clients discover available filter values
- [ ] **CAPNEG-02**: Tokens compact — terms table size-controlled to avoid excessive context consumption
- [ ] **CAPNEG-03**: Extends existing `search_kb`/`list_documents` tool descriptions or result annotations
- [ ] **CAPNEG-04**: Backend indexes the knowledge base for unique attribute values

### Phase 18: Grafana Datasource Fix

- [ ] **DSFIX-01**: Grafana dashboard loads without "Datasource ${DS_PROMETHEUS} was not found" errors when using `docker compose up -d`
- [ ] **DSFIX-02**: Stable UID (`uid: "prometheus"`) added to datasource provisioning config
- [ ] **DSFIX-03**: Hardcoded `"prometheus"` references replace `${DS_PROMETHEUS}` variables in both deployment dashboard JSONs (config + helm)
- [ ] **DSFIX-04**: `__inputs` sections removed from dashboard JSONs
- [ ] **DSFIX-05**: Helm chart updates produce same fix when monitoring is enabled

### Phase 19: VERIFICATION.md Backfill

- [ ] **VERBACK-01**: Every shipped phase without a VERIFICATION.md gets one (14 phases: 1-11.1, 12-13, 16-18)
- [ ] **VERBACK-02**: Each VERIFICATION.md documents verification criteria, commands, and results
- [ ] **VERBACK-03**: Backfill uses git log + test history to determine what was verified at ship time
- [ ] **VERBACK-04**: Backfill script for gap detection (list phases missing VERIFICATION.md)

### Phase 20: Test Environment Fixes

- [ ] **TESTFIX-01**: test_reranker_lazy.py conftest fixture isolation fixed — no cross-test pollution
- [ ] **TESTFIX-02**: All test files pass in clean environment (no stale .pyc, no cache artifacts)
- [ ] **TESTFIX-03**: Test suite self-contained — no external dependencies required for unit tests

### Phase 21: Codebase Hygiene Sweep

- [ ] **HYGIENE-01**: All unused imports removed across codebase
- [ ] **HYGIENE-02**: All TODO/FIXME/HACK comments resolved or tracked with issues
- [ ] **HYGIENE-03**: Type annotations consistent and mypy-clean
- [ ] **HYGIENE-04**: Log messages use consistent format and severity levels
- [ ] **HYGIENE-05**: Dead code (unused functions, classes, variables) removed

### Phase 22: Integration Checker CI Gate

- [ ] **CICHECK-01**: Integration checker script runs in CI after test execution
- [ ] **CICHECK-02**: Validates no integration gaps exist (docs ↔ code, plans ↔ implementation)
- [ ] **CICHECK-03**: CI fails if checker finds unresolved gaps
- [ ] **CICHECK-04**: Checker results reported in CI output for debugging

---

## Future Requirements

(none — scope complete for v1.3)

## Out of Scope

- Authentication / multi-user access control — internal tool, trusted network
- Cloud-managed vector store — self-hosted Qdrant only
- Real-time streaming ingest — file-based ingest only
- GUI for doc management — CLI + MCP tools sufficient
- LLM integration for classification — heuristics + metadata only

---

## Traceability

| REQ-ID      | Phase | Status        |
|-------------|-------|---------------|
| CAPNEG-01   | 17    | 🔄 Planned    |
| CAPNEG-02   | 17    | 🔄 Planned    |
| CAPNEG-03   | 17    | 🔄 Planned    |
| CAPNEG-04   | 17    | 🔄 Planned    |
| DSFIX-01    | 18    | 🔄 Planned    |
| DSFIX-02    | 18    | 🔄 Planned    |
| DSFIX-03    | 18    | 🔄 Planned    |
| DSFIX-04    | 18    | 🔄 Planned    |
| DSFIX-05    | 18    | 🔄 Planned    |
| VERBACK-01  | 19    | 🔄 Planned    |
| VERBACK-02  | 19    | 🔄 Planned    |
| VERBACK-03  | 19    | 🔄 Planned    |
| VERBACK-04  | 19    | 🔄 Planned    |
| TESTFIX-01  | 20    | 🔄 Planned    |
| TESTFIX-02  | 20    | 🔄 Planned    |
| TESTFIX-03  | 20    | 🔄 Planned    |
| HYGIENE-01  | 21    | 🔄 Planned    |
| HYGIENE-02  | 21    | 🔄 Planned    |
| HYGIENE-03  | 21    | 🔄 Planned    |
| HYGIENE-04  | 21    | 🔄 Planned    |
| HYGIENE-05  | 21    | 🔄 Planned    |
| CICHECK-01  | 22    | 🔄 Planned    |
| CICHECK-02  | 22    | 🔄 Planned    |
| CICHECK-03  | 22    | 🔄 Planned    |
| CICHECK-04  | 22    | 🔄 Planned    |
