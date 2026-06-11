# PHASE 3: Worker Pool and Rate Limiter - Implementation Plan

**Date**: 2026-05-15  
**Status**: 🔄 IN PROGRESS

## Goals
1. Async worker pool for parallel file processing
2. Global rate limiter to protect embedding API
3. JobExecutor to integrate scheduler with workers

## Deliverables

### 1. ingest/worker/limiter.py
- Rate limiter using token bucket or sliding window algorithm
- Configurable requests per minute/second
- Async-safe for concurrent workers
- Support for burst capacity

### 2. ingest/worker/worker.py
- Worker class for processing individual files
- Integration with rate limiter
- Error handling and retry logic
- Progress reporting to job manager

### 3. ingest/worker/pool.py
- WorkerPool class for managing multiple workers
- Dynamic worker scaling
- Task queue management
- Graceful shutdown

### 4. ingest/worker/executor.py
- JobExecutor to bridge scheduler and worker pool
- Job execution lifecycle
- Progress tracking integration
- Error recovery

## Acceptance Criteria
- ✅ Worker pool processes files in parallel
- ✅ Rate limiter enforces requests per minute
- ✅ JobExecutor integrates with JobManager and Scheduler
- ✅ Comprehensive tests for all components

## Directory Structure
```
ingest/
├── worker/
│   ├── __init__.py          # NEW
│   ├── limiter.py           # NEW: Rate limiter
│   ├── worker.py            # NEW: File worker
│   ├── pool.py              # NEW: Worker pool
│   └── executor.py          # NEW: Job executor
```

## Implementation Order
1. limiter.py - Rate limiting foundation
2. worker.py - Individual file processing
3. pool.py - Worker pool management
4. executor.py - Job execution orchestration
5. tests/test_worker_system.py - Comprehensive tests

## Integration Points
- **JobManager**: Update progress, report completion
- **Scheduler**: Get jobs to execute
- **ingest.py**: Will use executor instead of direct processing
- **Rate limiter**: Protect embedding API calls

## Key Design Decisions
- Use asyncio for concurrency (matches existing async code)
- Token bucket algorithm for rate limiting (allows bursts)
- WorkerPool uses asyncio.Queue for task distribution
- Graceful shutdown with task cancellation support

---

**Starting implementation...**
