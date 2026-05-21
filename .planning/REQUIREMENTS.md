# Requirements: v1.1 Quality & Operational Excellence

## Milestone Goal

Harden the server for real-world remote deployment (Python 3.13, starlette 1.0.0), expand test coverage with proper isolation mocking, and enforce a quality gate in CI.

---

## Active Requirements

### SSE Stability

- [ ] **SSE-01**: SSE `handle_sse` returns `Response()` on client disconnect; regression test covers starlette 1.0.0 behaviour on Python 3.13
- [ ] **SSE-02**: No `307 Temporary Redirect` loop on POST to `/messages/`; trailing-slash consistency between `SseServerTransport` path and `Mount` path verified by test

### Python 3.13 Compatibility

- [ ] **COMPAT-01**: All CI jobs run on Python 3.11 and Python 3.13 without failures or deprecation errors
- [ ] **COMPAT-02**: No Python 3.11-only syntax constructs remain that fail or warn on 3.13 (`asyncio.get_event_loop()`, deprecated typing aliases, etc.)

### Ingest Improvements

- [ ] **INGEST-01**: Ingested OTCS documents are auto-tagged by product area (WebReports, xECM, Workflow, CSIDE, etc.) based on filename/path heuristics, without requiring a manual `--product` flag
- [ ] **INGEST-02**: `kb-ingest status` CLI command shows last ingest time, total docs, total chunks, and error count per source directory

### Test Coverage & Isolation

- [ ] **TEST-01**: Every Python module in `kb_server/` and `ingest/` has a corresponding unit test file under `tests/`
- [ ] **TEST-02**: All unit tests run without requiring Qdrant, LM Studio, or Redis — all external dependencies are fully mocked at the transport/client boundary
- [ ] **TEST-03**: Integration tests are clearly marked with `pytest.mark.integration`; they can be skipped with `pytest -m "not integration"` and are separate from the unit test suite

### Logging Coverage

- [ ] **LOG-01**: Every public method in `kb_server/` emits at least one structured log entry at appropriate level (DEBUG for internal state, INFO for lifecycle events, WARNING/ERROR for failures)
- [ ] **LOG-02**: A logging coverage audit is run as part of CI; gaps identified and resolved before milestone closes

### Quality Gate

- [ ] **QUAL-01**: CI enforces ≥90% branch coverage on `kb_server/`; the build fails if coverage drops below the threshold
- [ ] **QUAL-02**: `pyproject.toml` `[tool.coverage.report]` `fail_under = 90` is set, tested, and verified to block a build when violated

### Documentation

- [ ] **DOC-01**: All public functions and classes in `kb_server/` and `ingest/` have English-language docstrings (one-line summary minimum)
- [ ] **DOC-02**: `docs/` folder is updated to reflect v1.1 changes: architecture diagram, ingest workflow, remote deployment guide for acemagic/LXC

---

## Future Requirements

- Source code comments and internal strings all in English (→ Backlog 999.1)
- README translations and Spanish README (→ Backlog 999.2)
- GUI for document management
- Authentication / access control layer
- Streaming ingest from external APIs

---

## Out of Scope

- Authentication / multi-user access control — internal tool, trusted network
- Cloud-managed vector store — self-hosted Qdrant only
- Real-time streaming ingest — file-based ingest only
- GUI — CLI + MCP tools sufficient

---

## Traceability

| REQ-ID | Phase | Plan |
|--------|-------|------|
| SSE-01 | Phase 5 | TBD |
| SSE-02 | Phase 5 | TBD |
| COMPAT-01 | Phase 5 | TBD |
| COMPAT-02 | Phase 5 | TBD |
| TEST-01 | Phase 6 | TBD |
| TEST-02 | Phase 6 | TBD |
| TEST-03 | Phase 6 | TBD |
| LOG-01 | Phase 7 | TBD |
| LOG-02 | Phase 7 | TBD |
| QUAL-01 | Phase 7 | TBD |
| QUAL-02 | Phase 7 | TBD |
| INGEST-01 | Phase 8 | TBD |
| INGEST-02 | Phase 8 | TBD |
| DOC-01 | Phase 8 | TBD |
| DOC-02 | Phase 8 | TBD |
