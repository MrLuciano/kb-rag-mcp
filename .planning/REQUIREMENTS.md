# Requirements: kb-rag-mcp

**Defined:** 2026-05-19
**Core Value:** AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.

## v1 Requirements

Requirements for the release-readiness milestone. All 16 features exist; this milestone closes integration gaps, removes debt, and hardens deployment.

### Codebase Cleanup

- [ ] **CLEAN-01**: Delete `server/` legacy module entirely; all imports and tests point to `kb_server/` only
- [ ] **CLEAN-02**: Fix hybrid search sparse path — `HybridSearcher` performs real dense+BM25 RRF fusion, not dense-only fallback
- [ ] **CLEAN-03**: Single `bootstrap_env()` function in `config/` replaces 6+ copy-pasted `load_dotenv` blocks across entry points
- [ ] **CLEAN-04**: Remove `ingest/registry.py` (v1 registry); only `ingest/core/metadata.py` remains
- [ ] **CLEAN-05**: Batch ingest computes real SHA-256 checksums per file (not hardcoded `"batch"` placeholder)

### Data Integrity & Security

- [ ] **DATA-01**: File watcher `on_deleted` handler removes vectors from Qdrant when source file is deleted
- [ ] **DATA-02**: `.env` and `config/.env.*` files removed from git tracking; only `config/.env.template` is committed
- [ ] **DATA-03**: `CONTRIBUTING.md` documents git history cleanup steps for teams that committed secrets (using `git-filter-repo`)

### Testing

- [ ] **TEST-01**: `kb_server/` package achieves ≥80% branch coverage
- [ ] **TEST-02**: End-to-end integration tests cover full path: ingest a document → query via `search_kb` MCP tool → verify result
- [ ] **TEST-03**: Integration tests cover multi-collection routing: route to correct collection, fallback on missing collection
- [ ] **TEST-04**: GitHub Actions CI pipeline runs full test suite on every push/PR to `master`

### Deployment

- [ ] **DEPL-01**: Production `Dockerfile` with multi-stage build producing a slim image
- [ ] **DEPL-02**: Quick-start script (`scripts/quickstart.sh`): clone → configure `.env` → start services → verify health
- [ ] **DEPL-03**: `README.md` end-to-end getting-started guide: install, configure, ingest docs, connect AI tool

## v2 Requirements

Deferred to a future milestone. Tracked but not in current roadmap.

### Distribution

- **DIST-01**: Docker Compose with Qdrant + kb-rag-mcp + optional Redis (full stack one-command)
- **DIST-02**: Published Docker image on Docker Hub or GHCR
- **DIST-03**: PyPI package for `kb_server` library

### Features

- **FEAT-01**: Web UI for document browsing and search (FASE 14 partially implemented)
- **FEAT-02**: OAuth / SSO support for team sharing
- **FEAT-03**: Streaming ingest from external HTTP sources (not just local files)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Authentication / access control | Internal trusted network; adds complexity without value for v1 |
| Cloud-managed vector store (Pinecone, Weaviate Cloud) | Data sovereignty — self-hosted Qdrant only |
| Mobile app or browser extension | Out of current scope; AI assistant MCP is the UI |
| Real-time streaming ingest from APIs | File-based ingest sufficient; complexity not justified |
| Multi-user permissions / RBAC | Internal tool; single-team use assumed |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLEAN-01 | Phase 1 | Pending |
| CLEAN-02 | Phase 1 | Pending |
| CLEAN-03 | Phase 1 | Pending |
| CLEAN-04 | Phase 1 | Pending |
| CLEAN-05 | Phase 1 | Pending |
| DATA-01 | Phase 2 | Pending |
| DATA-02 | Phase 2 | Pending |
| DATA-03 | Phase 2 | Pending |
| TEST-01 | Phase 3 | Pending |
| TEST-02 | Phase 3 | Pending |
| TEST-03 | Phase 3 | Pending |
| TEST-04 | Phase 3 | Pending |
| DEPL-01 | Phase 4 | Pending |
| DEPL-02 | Phase 4 | Pending |
| DEPL-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-19*
*Last updated: 2026-05-19 after initial definition*
