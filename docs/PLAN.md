# KB-RAG-MCP v2 Implementation Plan

## Overview
Transform KB-RAG-MCP into a production-ready system with job-based ingestion,
worker pool, caching, observability, and robust operations. This plan follows
TDD and includes a migration toolset.

## Constraints and Preferences
- Dependency management: pip-tools (requirements.in -> requirements.txt).
- Cache: in-memory LRU with auto-tuning; optional Redis fallback.
- Authentication: optional (AUTH_ENABLED=false by default, backward compatible). Bearer token auth available on SSE transport.
- Deployment: bare metal systemd for maximum performance.
- Redis: optional fallback only.
- Breaking changes: allowed during refactor.
- Test coverage: minimum 70% overall; critical paths prioritized.
- CLI: deprecate old commands with warnings (backward compatibility).
- Progress monitoring: configurable interval (default 2s).
- Error handling: continue processing and log failures.
- systemd: Restart=on-failure.
- Migration format: .tar.gz.

## Key Decisions
- Database rename: registry.db -> kb_metadata.db.
- Migrations: auto-run on connect with schema_version tracking.
- Cache default: auto-tune size based on available RAM.
- Rate limiter: global singleton to prevent embedding API overload.
- Job priority: 1-10 scale (10 highest) enforced by scheduler.
- Migration: offline only; Qdrant snapshot API is primary approach.
- Secrets handling: interactive prompts + --secrets-file.

## Timeline
Total duration: 24.6 weeks (172 days) — **ALL PHASES COMPLETE**

- ✅ FASE 1: Foundation and Testing Infrastructure (Days 1-10)
- ✅ FASE 1.5: Migration Tools (Days 11-12)
- ✅ FASE 2: Job Management and Scheduler (Days 13-24)
- ✅ FASE 3: Worker Pool and Rate Limiter (Days 25-35)
- ✅ FASE 4: Progress Tracking and Observability (Days 36-42)
- ✅ FASE 5: Cache System (Days 43-49)
- ✅ FASE 6: CLI Refactor and Job Control (Days 50-56)
- ✅ FASE 7: Document Validators and Quality (Days 57-63)
- ✅ FASE 8: Connection Pooling and Batch Optimization (Days 64-70)
- ✅ FASE 9: Production Hardening (Days 71-81)
- ✅ FASE 10: Documentation and Final QA (Days 82-88)
- ✅ FASE 11: Expanded Ingestion (Days 89-95)
- ✅ FASE 12: Search Quality Enhancement (Days 96-105)
- ✅ FASE 13: Ingestion Automation (Days 106-112)
- ✅ FASE 14: Observability and Audit (Days 113-122)
- ✅ FASE 15: Advanced Infrastructure (Days 123-136)
- ✅ FASE 16: RAG Performance and Accuracy (Days 137-150)
- ✅ QA Pipeline: QA evaluation (Hit Rate 100%, MRR 0.78)

## FASE 1: Foundation and Testing Infrastructure
Goals:
- Establish testing framework and fixtures.
- Introduce pip-tools dependency workflow.
- Add type hints to core modules.
- Provide CI-ready test commands.

Deliverables:
- requirements.in and requirements.txt via pip-tools.
- pytest setup, coverage config, tests/conftest.py.
- docs/TESTING.md describing test strategy.

Acceptance:
- pytest runs successfully.
- Coverage >70% for touched modules.

## FASE 1.5: Migration Tools (Offline)
Goals:
- Export and import complete KB state to .tar.gz package.
- Validate integrity with SHA256 manifest.
- Support secrets via prompts and file.

Deliverables:
- scripts/migrate/export.py, import.py, validate.py.
- scripts/kb-migrate.sh wrapper.
- docs/MIGRATION.md.
- tests for export/import/validate and E2E migration flow.

Acceptance:
- Export creates valid package.
- Import validates and restores KB state.

## FASE 2: Job Management and Scheduler
Goals:
- SQLite-backed job queue with lifecycle management.
- Priority scheduling and job persistence.

Deliverables:
- ingest/core/metadata.py with schema v2 (jobs, job_progress, files).
- ingest/job/manager.py, scheduler.py, models.py.
- Migration from v1 registry.

Acceptance:
- Jobs can be created, listed, paused, resumed, cancelled.
- Scheduler respects priority and concurrency limits.

## FASE 3: Worker Pool and Rate Limiter
Goals:
- Async worker pool for parallel file processing.
- Global rate limiter to protect embedding API.

Deliverables:
- ingest/worker/pool.py, worker.py, limiter.py.
- JobExecutor integrated with worker pool.

Acceptance:
- Worker pool processes files in parallel.
- Rate limiter enforces requests per minute.

## FASE 4: Progress Tracking and Observability
Goals:
- Real-time progress updates with configurable interval.
- Structured logging and Prometheus metrics.

Deliverables:
- observability/progress.py, metrics.py, logging.py.
- CLI progress command.

Acceptance:
- job progress --follow works with default 2s interval.
- Metrics exposed on /metrics endpoint.

## FASE 5: Cache System (LRU + Redis)
Goals:
- In-memory LRU cache for embeddings.
- Optional Redis fallback with promotion.

Deliverables:
- server/cache/* with CacheManager.
- embed_client.py integration.

Acceptance:
- Cache hit rate >80% for repeated queries.

## FASE 6: CLI Refactor and Job Control
Goals:
- New Click-based CLI with job commands.
- Legacy CLI wrapper with deprecation warnings.

Deliverables:
- ingest/cli/main.py, job.py, progress.py, legacy.py.
- Console entry points for kb-rag and legacy ingest.

Acceptance:
- Job commands work and legacy CLI remains functional.

## FASE 7: Document Validators and Quality
Goals:
- Validate format, size, and content quality before processing.

Deliverables:
- ingest/validation/* validators and pipeline.
- Worker integration.

Acceptance:
- Invalid files are skipped and logged with reasons.

## FASE 8: Connection Pooling and Batch Optimization
Goals:
- Connection pooling for embedding API and Qdrant.
- Batch embeddings and batch inserts.

Deliverables:
- embed_client.py batching.
- vector_store.py batch inserts.
- document_processor batch pipeline.

Acceptance:
- Batch path is >3x faster than sequential.

## FASE 9: Production Hardening
Goals:
- systemd services for server and scheduler.
- Health checks and log rotation.
- Monitoring dashboards.

Deliverables:
- deployment/systemd/*.service.
- deployment/scripts/install.sh, health-check.sh, backup.sh.
- Grafana dashboard and Prometheus configs.

Acceptance:
- Services restart on failure and pass health checks.

## FASE 10: Documentation and Final QA
Goals:
- Complete documentation and E2E tests.
- Performance benchmarks and security review.

Deliverables:
- docs/* references, troubleshooting, monitoring, security.
- E2E test suite and benchmarks.

Acceptance:
- Clean install works on Debian.
- Full workflow passes E2E tests.

---

## Future Phases: Enhancements and Advanced Features

### FASE 11: Expanded Ingestion (High + Medium Priority)
**Duration:** 7 days (Days 89-95)

Goals:
- Support legacy Office formats (doc, xls, ppt, WordPerfect).
- Extract and ingest ZIP archives recursively.
- Maximize document coverage for legacy documentation bases.

Deliverables:
- `ingest/parsers/legacy_office.py` with fallback chain:
  * python-docx2txt for .doc files
  * xlrd for old .xls files
  * python-pptx or textract for .ppt files
  * textract or unoconv for .wpd (WordPerfect)
  * odfpy for OpenDocument formats (.odt, .ods, .odp)
- `ingest/parsers/zip_handler.py`:
  * Recursive extraction up to 2 levels deep
  * Skip files >500MB inside archives
  * Preserve relative path as source_path metadata
  * Reuse existing parsers for extracted files
- Integration with existing parser factory in document_processor.py
- Validation rules for archive size and nesting depth
- Unit tests with real legacy format samples
- docs/LEGACY_FORMATS.md with supported formats table

Acceptance:
- Successfully ingests .doc, .xls, .ppt, .wpd files.
- Extracts and processes all files from nested ZIPs.
- Invalid formats fallback gracefully with logging.
- Test coverage >80% for new parsers.

---

### FASE 12: Search Quality Enhancement (High Priority)
**Duration:** 10 days (Days 96-105)

Goals:
- Implement payload indexing for fast filtered queries.
- Add hybrid search combining dense vectors with BM25 sparse.
- Integrate cross-encoder reranking for top results.
- Significantly improve retrieval quality (NDCG, MRR).

Deliverables:
- `scripts/migrations/create_payload_indexes.py`:
  * Create Qdrant payload indexes on `product` and `doc_type`
  * Safe to run on existing collections (idempotent)
  * Progress reporting for large collections
- `server/retrieval/hybrid_search.py`:
  * Integrate Qdrant SparseVector with BM25 from fastembed
  * Implement RRF (Reciprocal Rank Fusion) for score combination
  * Parameter `hybrid=true` in search_kb tool (opt-in)
  * Preserve existing filter compatibility
- `server/retrieval/reranker.py`:
  * Load cross-encoder/ms-marco-MiniLM-L-6-v2 via sentence-transformers
  * Retrieve top-20, rerank, return top-k
  * Parameter `rerank=true` in search_kb tool (opt-in)
  * Batch processing for efficiency (max 20 at a time)
  * Async implementation to avoid blocking
- Update `vector_store.py` to create indexes on collection creation
- Benchmarking suite: measure NDCG@5, MRR, recall before/after
- Integration tests with real queries
- Performance tests (latency p95 <500ms with reranking)
- docs/SEARCH_QUALITY.md with evaluation methodology

Acceptance:
- Payload indexes created on existing collections.
- Hybrid search improves recall by >15% on test dataset.
- Reranking improves NDCG@5 by >20% on test dataset.
- Opt-in parameters work without breaking existing behavior.
- Performance targets met (p95 <500ms).

---

### FASE 13: Ingestion Automation (Medium Priority)
**Duration:** 7 days (Days 106-112)

Goals:
- Auto-detect file changes and trigger incremental ingestion.
- Extract version information from filenames and index.
- Support per-directory metadata overrides with _meta.json.
- Reduce manual ingestion work.

Deliverables:
- `ingest/watcher/file_watcher.py`:
  * watchdog monitoring DOCS_PATH (configurable)
  * Debounce: 30s to avoid duplicate jobs
  * Trigger incremental ingestion via job system
  * Handle file create, modify, delete events
  * Ignore temp files (.tmp, .swp, etc.)
- `ingest/core/version_extractor.py`:
  * Regex patterns: `(\d{2}\.\d+)`, `(CE \d{2}\.\d+)`, `(v\d+\.\d+)`
  * Extract from filename and parent directory
  * Add `version` field to Qdrant payload (string)
  * Enable version filtering in search_kb tool
- `ingest/core/meta_loader.py`:
  * Load `_meta.json` per directory with schema:
    ```json
    {
      "product": "ProductName",
      "doc_type": "api_guide",
      "files": {
        "specific_file.pdf": {"product": "Override", "doc_type": "manual"}
      }
    }
    ```
  * Precedence: file-specific > directory-level > auto-inference
  * Validation: reject invalid product/doc_type values
- `deployment/systemd/kb-rag-watcher.service`:
  * Runs file_watcher as separate service
  * Restart=always
  * Depends on kb-rag-server
- Integration with FileScanner and metadata classification
- Unit tests for watcher, version extractor, meta loader
- Integration test: add file → watcher detects → job created
- docs/AUTO_INGESTION.md

Acceptance:
- Watcher detects new/modified files within 30s.
- Version extracted correctly from 90% of test filenames.
- _meta.json overrides work and take precedence.
- Watcher service runs continuously without crashes.

---

### FASE 14: Observability and Audit (Low Priority)
**Duration:** 10 days (Days 113-122)

Goals:
- Log all search queries with results and scores for analysis.
- Export file registry to CSV/JSON for auditing.
- Build lightweight web UI for document inspection and testing.
- Improve operational visibility.

Deliverables:
- `server/telemetry/query_logger.py`:
  * SQLite table `query_log`: query, top_k, product_filter, 
    doc_type_filter, num_results, avg_score, latency_ms, timestamp
  * Log after each search_kb invocation
  * Auto-rotation: keep last 90 days, monthly archive
  * Query to export aggregated stats (top queries, low-score queries)
- `ingest/cli/export.py`:
  * Command: `kb-rag registry export --format csv|json`
  * Options: --product, --doc_type, --status filters
  * Output: file_path, product, doc_type, status, ingested_at, hash
  * Streaming export for large registries (don't load all in memory)
- `server/ui/` (FastAPI + HTMX):
  * `/ui` - web interface (no auth, internal only)
  * Browse documents: list by product/doc_type, pagination (50/page)
  * Search tester: query input, show results with scores
  * Document detail: show chunks, metadata, source file
  * Bootstrap 5 or Tailwind for minimal styling
  * HTMX for dynamic updates without JS framework
- Update Grafana dashboard with query metrics:
  * Top 10 queries
  * Queries with low avg scores (<0.5)
  * Query latency p50/p95/p99
- Tests for query logger, export CLI, UI endpoints
- docs/QUERY_ANALYSIS.md

Acceptance:
- All queries logged with <5ms overhead.
- Export generates valid CSV/JSON with filters.
- UI allows browsing 10k+ documents with good UX.
- UI search tester returns same results as MCP tool.

---

### FASE 15: Advanced Infrastructure (Low Priority)
**Duration:** 14 days (Days 123-136)

Goals:
- Support multiple Qdrant collections (per product/context).
- Provide production-grade Kubernetes deployment.
- Enable horizontal scaling and multi-tenancy.

Deliverables:
- `server/collections/manager.py`:
  * CollectionManager: create, list, switch collections
  * Collection naming: `kb_docs_{product}` or `kb_docs_{context}`
  * Parameter `collection` in search_kb tool (optional)
  * Environment variable `DEFAULT_COLLECTION=kb_docs`
  * Automatic collection creation on first use
- `server/collections/router.py`:
  * Route queries to appropriate collection
  * Support wildcard: collection=* searches all collections
  * Merge and deduplicate results from multiple collections
- Helm chart: `deployment/kubernetes/kb-rag/`:
  * Chart.yaml, values.yaml
  * Deployments: kb-rag-server, kb-rag-health, kb-rag-scheduler
  * StatefulSet: qdrant (with PVC for data persistence)
  * ConfigMap: kb-rag.env configuration
  * Secret: embedding API keys (if needed)
  * Service: expose health server as LoadBalancer/NodePort
  * HPA (optional): autoscale server based on CPU >70%
  * Liveness/Readiness probes for all pods
  * Resource limits: 2Gi RAM server, 4Gi RAM Qdrant
- Alternative: plain YAML manifests if Helm not required
- `deployment/kubernetes/kb-rag-sqlite-backup.yaml`:
  * CronJob for daily backups to PVC
- Update install.sh to detect k8s environment
- Integration tests with kind or minikube
- docs/KUBERNETES.md with deployment guide

Acceptance:
- Multi-collection support works with filtering.
- Helm install creates all resources successfully.
- Pods restart on failure with health checks.
- Backup CronJob runs and creates valid archives.
- Services accessible via LoadBalancer or Ingress.

---

### FASE 16: RAG Performance and Accuracy (Low Priority)
**Duration:** 14 days (Days 137-150)

Goals:
- Establish RAG evaluation methodology with metrics.
- Analyze query patterns from production logs.
- Implement continuous improvement pipeline.
- Optimize RAG based on real usage data (not LLM training).

Deliverables:
- `server/analytics/query_analyzer.py`:
  * Load query_log from FASE 14
  * Identify patterns: most common queries, low-score queries
  * Cluster similar queries (embeddings + k-means)
  * Generate report: query_analysis.json
- `server/evaluation/ragas_pipeline.py`:
  * Golden dataset: 50+ (query, expected_answer, expected_docs)
  * RAGAS metrics: context_precision, answer_relevancy, 
    faithfulness, context_recall
  * LLM-as-judge using local Ollama or OpenAI API
  * Compare current system vs improvements
  * Store results in `evaluation_results.json`
- `server/evaluation/dataset.py`:
  * Create golden dataset from real queries (anonymized)
  * Manual labeling: expected answer, expected source docs
  * Version control for dataset (git)
- Optimization experiments based on analysis:
  * Adjust CHUNK_SIZE/CHUNK_OVERLAP based on doc types
  * Tune score thresholds per product
  * Optimize reranking model selection
  * Experiment with query expansion/reformulation
- CI job: weekly RAGAS evaluation on main branch
- Regression tests: alert if RAGAS scores drop >10%
- Before/after reports with charts
- docs/RAG_EVALUATION.md:
  * Methodology
  * Baseline metrics
  * Improvement experiments
  * Results and recommendations

Acceptance:
- Golden dataset created with 50+ labeled examples.
- RAGAS pipeline runs and produces metrics.
- At least 2 optimization experiments completed.
- Improvement of >10% in at least one RAGAS metric.
- Evaluation runs automatically in CI weekly.

---

## Updated Timeline

Total duration: 24.6 weeks (172 days) — **ALL PHASES COMPLETE**

**Completed Phases (Days 1-150):**
- FASE 1-10: Foundation through Documentation (88 days)
- FASE 11: Expanded Ingestion (7 days)
- FASE 12: Search Quality Enhancement (10 days)
- FASE 13: Ingestion Automation (7 days)
- FASE 14: Observability and Audit (10 days)
- FASE 15: Advanced Infrastructure (14 days)
- FASE 16: RAG Performance and Accuracy (14 days)
- QA Pipeline: QA evaluation — Hit Rate 100%, MRR 0.78 ✅

**v1.4 (FASEs 29-37): Platform, Analytics & Enterprise (Phases scheduled: 2026-05-27 to 2026-06-11):**
- FASE 29: Enterprise Data Source Connectors — Confluence, JIRA, Git remote ingestion
- FASE 30: Cross-Doc Knowledge Graph — Graph metadata derivation, related doc discovery
- FASE 31: MCP Prompt Templates — extract_answer + summarize_documents prompts
- FASE 32: API Key Authentication — Optional Bearer token auth on SSE
- FASE 33: Request Rate Limiting — Per-subject token bucket server enforcement
- FASE 34: Upload Index Quotas — Per-KB upload limits, schema v3→v4
- FASE 35: Multi-KB Aggregated Search — kb_ids parameter, RRF multi-collection merge
- FASE 36: Provider Budget & Circuit Breaker — Provider resilience, fallback chain
- FASE 37: Request-level Retrieval Cache — Query result cache with invalidation

**Total:** ~8.5 months for complete feature set — **DELIVERED**

---

## Priority Execution Order

All phases shipped. No pending phases.

**v1.0 (FASEs 1-10):** Foundation, job system, worker pool, cache, CLI, validators, batching, production hardening, documentation.

**v1.1.0 (FASEs 11-12):** Expanded ingestion (legacy Office, ZIP), search quality (hybrid BM25+dense, reranker).

**v1.2.0 (FASEs 13-14):** Ingestion automation (file watcher, version extractor), observability (query logger, web UI).

**v1.3.0 (FASEs 15-16 + QA):** Advanced infrastructure (multi-collection, Kubernetes), RAG accuracy (RAGAS pipeline, golden dataset), QA pipeline validated.

**v1.4.0 (FASEs 29-37):** Platform, Analytics & Enterprise — Connectors, knowledge graph, MCP prompts, auth, rate limiting, quotas, multi-KB search, circuit breaker, retrieval cache.
