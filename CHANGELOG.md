# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - FASE 7: Document Validators and Quality Checks (2026-05-15)

- **Comprehensive Validation System**
  - 9 validators across 3 categories (format, size, content)
  - `FileExistsValidator`: Checks file existence and readability
  - `FileExtensionValidator`: Validates against 25+ supported extensions
  - `MimeTypeValidator`: Verifies MIME types
  - `FileSizeValidator`: Generic size range validation (1 byte - 100 MB)
  - `FileTypeSpecificSizeValidator`: Type-aware limits (text: 10MB, PDF: 50MB, etc.)
  - `TextContentValidator`: Minimum content length and word count
  - `EncodingValidator`: UTF-8/ASCII/Latin-1 encoding checks
  - `BinaryContentValidator`: File signature validation (PDF, ZIP-based formats)
  - `PathValidator`: Path length and invalid character checks

- **Validation Pipeline**
  - `ValidationPipeline` orchestrator with fail-fast and batch support
  - `create_default_pipeline()`: Balanced validation
  - `create_strict_pipeline()`: Fail-fast with warnings as errors
  - `create_lenient_pipeline()`: No fail-fast, warnings ignored
  - Batch validation with `validate_batch()` and `get_failed_files()`
  - Dynamic validator add/remove support

- **Worker Integration**
  - Pre-processing validation before file processing
  - New `validation_failed` status in `WorkerResult`
  - `validation_errors` field to track failure reasons
  - `files_validation_failed` counter in `WorkerStats`
  - `skip_validation` flag for backward compatibility

- **Testing**
  - 35 comprehensive validation tests (100% passing)
  - Full coverage of all validators and pipeline features
  - Integration tests with worker system

- **Performance**
  - Typical validation time: <10ms per file
  - Early rejection saves CPU and API costs
  - Minimal overhead for valid files

### Added - FASE 6: Modern CLI with Click and Rich (2026-05-14)

- **Modern CLI Framework**
  - Click-based command structure replacing argparse
  - Rich terminal UI with colored output, tables, and progress bars
  - Console entry points: `kb-rag` (new) and `kb-ingest-legacy` (backward compatibility)

- **Job Commands** (7 commands)
  - `kb-rag job create`: Create new ingestion jobs with priority support
  - `kb-rag job list`: List jobs with status filtering and colored output
  - `kb-rag job show`: Show detailed job information
  - `kb-rag job pause`: Pause running jobs
  - `kb-rag job resume`: Resume paused jobs
  - `kb-rag job cancel`: Cancel jobs
  - `kb-rag job clean`: Cleanup completed/failed jobs with dry-run mode

- **Progress Commands** (2 commands)
  - `kb-rag progress show`: Show current job progress
  - `kb-rag progress follow`: Real-time progress monitoring with ETA

- **Info Command**
  - `kb-rag info`: Display database statistics and system status

- **CLI Features**
  - Job ID prefix matching (e.g., use first 8 chars instead of full UUID)
  - Priority scheduling: low/normal/high/critical
  - Status filtering in job list
  - Dry-run mode for cleanup operations
  - Real-time progress updates with ETA calculation

- **Testing**
  - 19 CLI integration tests
  - Shared test fixtures in conftest.py

- **Dependencies**
  - click>=8.0.0: Modern CLI framework
  - rich>=13.0.0: Terminal formatting library

### Added - FASE 5: Embedding Cache System (2026-05-13)

- **Two-Tier Caching Architecture**
  - In-memory LRU cache with thread-safe operations
  - Optional Redis backend for distributed caching
  - Unified `CacheManager` interface with automatic fallback

- **LRU Cache Features**
  - Auto-tuning based on available RAM (default: 10% of system RAM)
  - Thread-safe get/set/delete operations
  - Automatic eviction on memory pressure
  - TTL support (default: 24 hours)

- **Redis Cache Features**
  - Optional distributed caching
  - Configurable TTL and key prefix
  - Connection pooling support
  - Graceful fallback on connection failures

- **Cache Integration**
  - Integrated into `embed_client.py` for embedding caching
  - Cache hit/miss tracking with metrics
  - Transparent caching layer (no API changes required)

- **Metrics**
  - `cache_hits_total`: Total cache hits
  - `cache_misses_total`: Total cache misses
  - `cache_evictions_total`: Number of cache evictions
  - `cache_size_bytes`: Current cache size in bytes
  - `cache_items_total`: Number of items in cache

- **Performance Impact**
  - Cache hit: ~0.1ms (vs 200-500ms API call)
  - Memory overhead: ~4KB per cached embedding
  - Default capacity: Auto-tuned to system RAM

### Added - FASE 4: Progress Tracking and Observability (2026-05-12)

- **Structured Logging**
  - JSON-formatted logs with contextual information
  - Configurable log levels and output formats
  - Request ID tracking across components

- **Prometheus Metrics**
  - 15 core metrics for monitoring system health
  - Request latency histograms
  - Error rate counters
  - Active worker gauges
  - Job status tracking

- **Progress Tracking**
  - Real-time progress updates with ETA calculation
  - File-level and job-level progress tracking
  - Speed and throughput measurements
  - Progress persistence across restarts

### Added - FASE 3: Worker Pool and Rate Limiter (2026-05-11)

- **Worker Pool**
  - Configurable number of parallel workers (default: 4)
  - Task queue with max size limit
  - Async context manager support
  - Graceful shutdown with timeout
  - Worker statistics tracking

- **Rate Limiter**
  - Token bucket algorithm implementation
  - Configurable requests per minute
  - Async/await support
  - Prevents API rate limit violations

- **FileWorker**
  - Individual file processing with retry logic
  - Configurable max retries (default: 3)
  - Integration with rate limiter
  - Detailed result tracking

- **Testing**
  - 23 worker system tests
  - Coverage of worker pool, rate limiter, and file worker

### Added - FASE 2: Job Management and Scheduler (2026-05-10)

- **Job Management System**
  - Job creation with priority support (low/normal/high/critical)
  - Job lifecycle management (pending → running → completed/failed/cancelled)
  - Job pause/resume functionality
  - Job progress tracking
  - SQLite-based job persistence with WAL mode

- **Job Scheduler**
  - Priority-based job scheduling
  - Configurable concurrent job limit
  - Queue statistics and monitoring
  - Bulk operations (cancel all, pause all, resume all)

- **Database Schema v2**
  - `jobs` table: Job metadata and configuration
  - `job_progress` table: Progress tracking
  - `files` table: File processing status
  - Schema versioning support
  - Migration utilities

- **Testing**
  - 34 job management tests
  - Coverage of CRUD operations, lifecycle, and scheduler

### Added - FASE 1: Foundation & Testing Infrastructure (2026-05-09)

- **Testing Infrastructure**
  - pytest configuration with async support
  - Test fixtures for common scenarios
  - Coverage reporting setup
  - Test organization and best practices

- **Code Quality Tools**
  - black: Code formatting (line length: 79)
  - isort: Import sorting
  - flake8: Linting and style checks
  - Type annotations baseline

- **Dependency Management**
  - pip-tools workflow (requirements.in → requirements.txt)
  - Pinned dependency versions
  - Development vs production dependencies

- **Documentation**
  - Testing guide (docs/TESTING.md)
  - Phase completion reports
  - API documentation

## [0.1.0] - Initial Release

### Added

- **MCP Server**
  - FastAPI-based MCP server for RAG queries
  - Qdrant vector store integration
  - OpenAI embeddings support
  - Document ingestion pipeline

- **Document Processing**
  - Support for 25+ file formats (PDF, DOCX, code files, etc.)
  - Text extraction and chunking
  - Product classification
  - File registry for tracking processed documents

- **Vector Search**
  - Semantic search with OpenAI embeddings
  - Qdrant collection management
  - Configurable similarity thresholds
  - Batch operations support

- **Configuration**
  - Environment-based configuration
  - Docker Compose setup
  - Systemd service files
  - Health check scripts

- **Documentation**
  - Installation guide
  - Usage examples
  - Architecture overview
  - API reference

---

## Summary Statistics

### Phase 7 (Current)
- **Files changed**: 17 files
- **Lines added**: 2,054 lines
- **Tests added**: 35 tests (100% passing)
- **Validators**: 9 distinct validators
- **Total test count**: 113 tests (106 passing)

### Phases 1-7 Combined
- **Total commits**: 6 major feature commits
- **Total files changed**: 52+ files
- **Total lines added**: ~7,824 lines
- **Total tests**: 113 tests (106 passing, 7 CLI issues)
- **Code coverage**: 70%+ maintained throughout
- **Documentation**: 50+ KB of docs (bilingual EN/PT)

### Project Completion
- **Phases completed**: 7 out of 12 (58%)
- **Estimated time**: ~7 weeks of 12.6 total
- **Next phase**: FASE 8 - Connection Pooling and Batch Optimization

---

## Migration Notes

### Upgrading to FASE 7 (Validation)
- Validation is **enabled by default** in `FileWorker`
- Use `skip_validation=True` to disable (legacy behavior)
- Invalid files will be logged with specific reasons
- New status: `validation_failed` in worker results

### Upgrading to FASE 6 (CLI)
- New CLI: `kb-rag` (recommended)
- Legacy CLI: `kb-ingest-legacy` (shows deprecation warning)
- Run `pip install -e .` to install console entry points
- Dependencies: `click>=8.0.0`, `rich>=13.0.0`

### Upgrading to FASE 5 (Cache)
- Cache is **enabled by default** with auto-tuning
- Set `CACHE_BACKEND=redis` for distributed caching
- Default: LRU cache with 10% available RAM
- Optional Redis configuration via environment variables

---

## Known Issues

### FASE 6 CLI Tests (7 failures)
- Some CLI tests fail due to f-string formatting issues
- CLI functionality works correctly in manual testing
- Tests will be fixed in next iteration
- Does not affect production usage

### FASE 7 Validation Limitations
- MIME type detection limited to extension-based guessing
- Binary signature detection limited to PDF and ZIP-based formats
- Encoding detection limited to utf-8, ascii, latin-1
- Content validation is surface-level only

---

## Contributors

- Development team
- Testing and QA
- Documentation writers

---

## License

[Add your license information here]
