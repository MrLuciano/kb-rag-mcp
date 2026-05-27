# Requirements: v1.3 Post-Ship Polish & Infrastructure

## Milestone Goal

Post-v1.2 enhancements: English-only enforcement, multilingual README, Prometheus observability, Windows LAN access, and reclassification capability for document metadata updates.

---

## Active Requirements

### Operational Debt

- [ ] **DEBT-01**: Cross-encoder model loads lazily on first `predict()` call, not at import time — saves ~500MB memory and ~10s startup latency
- [x] **DEBT-02**: Helm chart is validated with `helm lint` in CI pipeline — catches structural errors before deployment
- [x] **DEBT-03**: MagicMock pollution from `qdrant_client` sys.modules stubs is resolved across the test suite — enum values compare correctly without `getattr(x, 'value', x)` workaround
- [ ] **DEBT-04**: Server startup performs pre-flight health check — warns if Qdrant or LM Studio are unreachable before accepting queries
- [ ] **DEBT-05**: Logging coverage is enforced via CI gate (`--fail-under` threshold) — prevents regression below current baseline
- [ ] **DEBT-06**: LM Studio embedding dependency is documented with recommended fallback/startup options in operations guide

### Auto-Classification (Phase 11 - COMPLETE)

- [x] **CLASSIFY-01**: Documents are auto-classified with Vendor, Product, Subsystem, and Version attributes — inferred from directory hierarchy and filename patterns, extending existing OTCS product detection
- [x] **CLASSIFY-02**: Classification gaps are filled by extracting metadata (title, subject, author) and first-page content from PDF/DOCX files — no LLM dependency
- [x] **CLASSIFY-03**: Extended classification is backward-compatible with existing OTCS auto-tagging — existing `infer_product()` and `infer_doc_type()` signatures unchanged

### Reclassification (Phase 16 - PLANNING)

- [ ] **RECLASSIFY-01**: In-place metadata updates in Qdrant preserve embeddings and vectors — VectorStore provides `update_chunk_metadata()` for fast payload-only updates
- [ ] **RECLASSIFY-02**: SQLite backup/audit tables (`reclassify_backups`, `reclassify_history`) enable full rollback and change tracking — integrated with IngestRegistry in `data/registry.db`
- [ ] **RECLASSIFY-03**: Classification detection compares current Qdrant metadata against `classify()` output — only updates documents where metadata differs
- [ ] **RECLASSIFY-04**: CLI subcommand `kb-ingest reclassify <pattern>` provides interactive preview and confirmation — shows aggregated summary by field before applying changes
- [ ] **RECLASSIFY-05**: Dedicated verify subcommand shows mismatches between current and expected metadata — useful before and after reclassification
- [ ] **RECLASSIFY-06**: Session-based and selective rollback restore old metadata from backup — supports full session undo or pattern+timestamp selective restore
- [ ] **RECLASSIFY-07**: Documentation covers reclassification workflows, safety mechanisms, and operational procedures — integrated into README (user guide) and OPERATIONS.md (ops guide)

---

## Future Requirements

- LLM-assisted classification for ambiguous documents (post-v1.2)
- Reclassification of already-ingested documents (depends on CLASSIFY-01/02)
- English inline comments sweep (Backlog 999.1)
- README translations + Spanish README (Backlog 999.2)

## Out of Scope

- Authentication / multi-user access control — internal tool, trusted network
- Cloud-managed vector store — self-hosted Qdrant only
- Real-time streaming ingest — file-based ingest only
- GUI for doc management — CLI + MCP tools sufficient
- LLM integration for classification — heuristics + metadata only in v1.2

---

## Traceability

| REQ-ID | Phase | Plan | Status |
|--------|-------|------|--------|
| DEBT-01 | Phase 9 | 09-01 | ✅ Complete |
| DEBT-04 | Phase 9 | 09-02 | ✅ Complete |
| DEBT-06 | Phase 9 | 09-03 | ✅ Complete |
| DEBT-02 | Phase 10 | 10-01 | ✅ Complete |
| DEBT-03 | Phase 10 | 10-02 | ✅ Complete |
| DEBT-05 | Phase 10 | 10-03 | ✅ Complete |
| CLASSIFY-01 | Phase 11 | 11-01 | ✅ Complete |
| CLASSIFY-02 | Phase 11 | 11-02 | ✅ Complete |
| CLASSIFY-03 | Phase 11 | 11-01+02 | ✅ Complete |
| RECLASSIFY-01 | Phase 16 | 16-01 | 🔄 Planning |
| RECLASSIFY-02 | Phase 16 | 16-01 | 🔄 Planning |
| RECLASSIFY-03 | Phase 16 | 16-01 | 🔄 Planning |
| RECLASSIFY-04 | Phase 16 | 16-02 | 🔄 Planning |
| RECLASSIFY-05 | Phase 16 | 16-02 | 🔄 Planning |
| RECLASSIFY-06 | Phase 16 | 16-02 | 🔄 Planning |
| RECLASSIFY-07 | Phase 16 | 16-03 | 🔄 Planning |
