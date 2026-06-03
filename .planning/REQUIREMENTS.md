# Requirements: kb-rag-mcp

**Defined:** 2026-05-27
**Core Value:** AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.

## v1 Requirements

### Documentation

- [ ] **DOCS-01**: User can find docs organized by deployment mode (Docker Compose, Helm, systemd, manual) from README/OPERATIONS/TROUBLESHOOTING
- [ ] **DOCS-02**: Each deployment path has a dedicated doc file as single source of truth
- [ ] **DOCS-03**: CHANGELOG updated with all v1.3/v1.4 changes
- [ ] **DOCS-04**: REFERENCE.md updated with all v1.3/v1.4 changes

### RAGAS Evaluation

- [ ] **EVAL-01**: User can run RAGAS evaluation with 4 core metrics (faithfulness, answer_relevancy, context_precision, context_recall)
- [ ] **EVAL-02**: User can load golden Q&A dataset from CSV/JSON for evaluation
- [ ] **EVAL-03**: RAGAS evaluation reuses existing LM Studio/Ollama backend for LLM-as-judge scoring
- [ ] **EVAL-04**: User can export evaluation results as CSV with console summary table

### Optimization Experiments

- [ ] **OPT-01**: User can run chunking experiments with configurable strategies (fixed, recursive, semantic)
- [ ] **OPT-02**: User can run scoring/reranking experiments comparing cross-encoder to other strategies
- [ ] **OPT-03**: User can view comparison metrics (recall@K, MRR) across experiment runs

## Active Requirements (v1.4)

### Enterprise Data Source Connectors (Phase 29)

- [ ] **ENT-01**: User can ingest documents from Confluence, JIRA, and Git sources without exporting files manually
- [ ] **ENT-02**: Connector sync tracks stable remote identities and incremental changes using source-specific checkpoints
- [ ] **ENT-03**: Connector-fetched content reuses the existing parsing, chunking, embedding, and registry pipeline through staged local artifacts
- [ ] **ENT-04**: CLI exposes connector registration and sync commands without breaking existing local-file ingest flows

### Cross-Document Knowledge Graph (Phase 30)

- [ ] **GRAPH-01**: Ingest pipeline derives graph metadata linking related documents, entities, or topics within a KB
- [ ] **GRAPH-02**: MCP surface exposes graph-aware discovery for related documents and graph summaries without regressing existing search tools
- [ ] **GRAPH-03**: Vector store and metadata persistence support graph fields and indexes with backward-compatible behavior for existing collections

### MCP Prompt Templates (Phase 31)

- [ ] **MCPPROMPTS-01**: MCP server exposes prompt discovery via `prompts/list` for at least grounded-answer and summarize-documents prompts
- [ ] **MCPPROMPTS-02**: MCP server renders prompt content via `get_prompt` using current KB semantics and citation conventions
- [ ] **MCPPROMPTS-03**: Prompt support is additive only — existing tools, resources, and transports remain unchanged

### API Key Authentication (Phase 32)

- [ ] **AUTH-01**: HTTP-facing MCP transports require optional API key authentication while stdio transport remains unchanged
- [ ] **AUTH-02**: API keys are stored hashed with revocation metadata and can be scoped globally or to a specific KB
- [ ] **AUTH-03**: CLI/admin flows can create, list, and revoke API keys without exposing plaintext keys after creation

### Request Rate Limiting (Phase 33)

- [ ] **RATE-01**: Server enforces token-bucket rate limiting per subject on MCP HTTP requests and MCP tool invocations
- [ ] **RATE-02**: Rate limiter emits Prometheus metrics for allowed, delayed, and rejected requests
- [ ] **RATE-03**: Rate limiting degrades appropriately by transport (HTTP 429 for HTTP transports, MCP error payload for stdio)

### Upload and Index Quotas (Phase 34)

- [ ] **QUOTA-01**: Durable quota limits exist for files, bytes, chunks, documents, and characters at ingest/job boundaries
- [ ] **QUOTA-02**: Quota enforcement covers both direct ingest and worker/job execution paths so no ingest path bypasses limits
- [ ] **QUOTA-03**: Operators can inspect or change quota settings through CLI/admin surfaces with usage tracking persisted in metadata storage

### Multi-KB Aggregated Search (Phase 35)

- [ ] **MULTIKB-01**: `search_kb` accepts multiple KB identifiers and fans out queries across their mapped collections
- [ ] **MULTIKB-02**: Aggregated results preserve provenance, normalize ranking, and deduplicate equivalent hits across KBs
- [ ] **MULTIKB-03**: Existing single-KB collection and `kb_id` search behavior remains backward compatible

### Provider Budget & Circuit Breaker (Phase 36)

- [ ] **PROVBUD-01**: Embedding provider calls enforce configurable request budgets and failure thresholds per backend
- [ ] **PROVBUD-02**: Circuit breaker state supports closed, open, and half-open transitions with cooldown and fallback behavior
- [ ] **PROVBUD-03**: Provider resilience emits operational metrics without regressing existing embed client APIs

### Request-level Retrieval Cache (Phase 37)

- [ ] **RLCACHE-01**: Search requests can be served from an in-memory request-result cache keyed by query, KB scope, filters, and retrieval options
- [ ] **RLCACHE-02**: Retrieval cache invalidates on TTL expiry and on retrieval-affecting state changes such as ingest or reclassification
- [ ] **RLCACHE-03**: Cached search responses still integrate with existing logging and observability paths

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time A/B testing in production | Experiments are offline/analysis only |
| Agentic chunking | Too experimental for this milestone |
| RAGAS metrics beyond 4 core | Keep evaluation focused; add later if needed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DOCS-01 | Phase 23 | ✅ Complete |
| DOCS-02 | Phase 23 | ✅ Complete |
| DOCS-03 | Phase 23 | ✅ Complete |
| DOCS-04 | Phase 23 | ✅ Complete |
| EVAL-01 | Phase 24 | Deferred |
| EVAL-02 | Phase 24 | Deferred |
| EVAL-03 | Phase 24 | Deferred |
| EVAL-04 | Phase 24 | Deferred |
| OPT-01 | Phase 25 | Deferred |
| OPT-02 | Phase 25 | Deferred |
| OPT-03 | Phase 25 | Deferred |
| DISC-01 | Phase 26 | ✅ Complete |
| DISC-02 | Phase 26 | ✅ Complete |
| DISC-03 | Phase 26 | ✅ Complete |
| DISC-04 | Phase 26 | ✅ Complete |
| DISC-05 | Phase 26 | ✅ Complete |
| DISC-06 | Phase 26 | ✅ Complete |
| KBREG-01 | Phase 27 | ✅ Complete |
| KBREG-02 | Phase 27 | ✅ Complete |
| MCPHTTP-01 | Phase 28 | Pending |
| ENT-01 | Phase 29 | Pending |
| ENT-02 | Phase 29 | Pending |
| ENT-03 | Phase 29 | Pending |
| ENT-04 | Phase 29 | Pending |
| GRAPH-01 | Phase 30 | Pending |
| GRAPH-02 | Phase 30 | Pending |
| GRAPH-03 | Phase 30 | Pending |
| MCPPROMPTS-01 | Phase 31 | Pending |
| MCPPROMPTS-02 | Phase 31 | Pending |
| MCPPROMPTS-03 | Phase 31 | Pending |
| AUTH-01 | Phase 32 | Pending |
| AUTH-02 | Phase 32 | Pending |
| AUTH-03 | Phase 32 | Pending |
| RATE-01 | Phase 33 | Pending |
| RATE-02 | Phase 33 | Pending |
| RATE-03 | Phase 33 | Pending |
| QUOTA-01 | Phase 34 | Pending |
| QUOTA-02 | Phase 34 | Pending |
| QUOTA-03 | Phase 34 | Pending |
| MULTIKB-01 | Phase 35 | Pending |
| MULTIKB-02 | Phase 35 | Pending |
| MULTIKB-03 | Phase 35 | Pending |
| PROVBUD-01 | Phase 36 | Pending |
| PROVBUD-02 | Phase 36 | Pending |
| PROVBUD-03 | Phase 36 | Pending |
| RLCACHE-01 | Phase 37 | Pending |
| RLCACHE-02 | Phase 37 | Pending |
| RLCACHE-03 | Phase 37 | Pending |

**Coverage:**
- v1 requirements: 36 total
- Mapped to phases: 36
- Unmapped: 0 ✓

---

*Requirements defined: 2026-05-27*
*Last updated: 2026-06-03 after v1.4 planning update (phases 29–37)*
