# Requirements: v1.2 Tech Debt & Classification

## Milestone Goal

Resolve accumulated technical debt from v1.0/v1.1 while adding automated document classification with Vendor/Product/Subsystem/Version extraction.

---

## Active Requirements

### Operational Debt

- [ ] **DEBT-01**: Cross-encoder model loads lazily on first `predict()` call, not at import time — saves ~500MB memory and ~10s startup latency
- [ ] **DEBT-02**: Helm chart is validated with `helm lint` in CI pipeline — catches structural errors before deployment
- [ ] **DEBT-03**: MagicMock pollution from `qdrant_client` sys.modules stubs is resolved across the test suite — enum values compare correctly without `getattr(x, 'value', x)` workaround
- [ ] **DEBT-04**: Server startup performs pre-flight health check — warns if Qdrant or LM Studio are unreachable before accepting queries
- [ ] **DEBT-05**: Logging coverage is enforced via CI gate (`--fail-under` threshold) — prevents regression below current baseline
- [ ] **DEBT-06**: LM Studio embedding dependency is documented with recommended fallback/startup options in operations guide

### Auto-Classification

- [ ] **CLASSIFY-01**: Documents are auto-classified with Vendor, Product, Subsystem, and Version attributes — inferred from directory hierarchy and filename patterns, extending existing OTCS product detection
- [ ] **CLASSIFY-02**: Classification gaps are filled by extracting metadata (title, subject, author) and first-page content from PDF/DOCX files — no LLM dependency
- [ ] **CLASSIFY-03**: Extended classification is backward-compatible with existing OTCS auto-tagging — existing `infer_product()` and `infer_doc_type()` signatures unchanged

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

| REQ-ID | Phase | Plan |
|--------|-------|------|
| DEBT-01 | Phase 9 | TBD |
| DEBT-04 | Phase 9 | TBD |
| DEBT-06 | Phase 9 | TBD |
| DEBT-02 | Phase 10 | TBD |
| DEBT-03 | Phase 10 | TBD |
| DEBT-05 | Phase 10 | TBD |
| CLASSIFY-01 | Phase 11 | TBD |
| CLASSIFY-02 | Phase 11 | TBD |
| CLASSIFY-03 | Phase 11 | TBD |
