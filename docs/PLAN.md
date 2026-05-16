# KB-RAG-MCP v2 Implementation Plan

## Overview
Transform KB-RAG-MCP into a production-ready system with job-based ingestion,
worker pool, caching, observability, and robust operations. This plan follows
TDD and includes a migration toolset.

## Constraints and Preferences
- Dependency management: pip-tools (requirements.in -> requirements.txt).
- Cache: in-memory LRU with auto-tuning; optional Redis fallback.
- Authentication: none (internal, trusted use).
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
Total duration: 12.6 weeks (88 days)

- FASE 1: Foundation and Testing Infrastructure (Days 1-10)
- FASE 1.5: Migration Tools (Days 11-12)
- FASE 2: Job Management and Scheduler (Days 13-24)
- FASE 3: Worker Pool and Rate Limiter (Days 25-35)
- FASE 4: Progress Tracking and Observability (Days 36-42)
- FASE 5: Cache System (Days 43-49)
- FASE 6: CLI Refactor and Job Control (Days 50-56)
- FASE 7: Document Validators and Quality (Days 57-63)
- FASE 8: Connection Pooling and Batch Optimization (Days 64-70)
- FASE 9: Production Hardening (Days 71-81)
- FASE 10: Documentation and Final QA (Days 82-88)

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
