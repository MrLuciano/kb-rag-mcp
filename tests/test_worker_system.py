"""
Tests for FASE 3: Worker Pool and Rate Limiter.

Tests rate limiter, file worker, worker pool, and job executor.
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ingest.worker.limiter import MultiRateLimiter, RateLimiter
from ingest.worker.pool import WorkerPool, WorkerTask
from ingest.worker.worker import FileWorker, WorkerResult, WorkerStats

# ── RateLimiter Tests


@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """Test basic rate limiter functionality."""
    limiter = RateLimiter(requests_per_minute=60.0)  # 1 req/sec

    # Should acquire immediately
    start = asyncio.get_event_loop().time()
    await limiter.acquire()
    elapsed = asyncio.get_event_loop().time() - start

    assert elapsed < 0.1  # Should be instant


@pytest.mark.asyncio
async def test_rate_limiter_enforces_rate():
    """Test that rate limiter enforces rate limit."""
    limiter = RateLimiter(
        requests_per_minute=120.0, burst_capacity=2
    )  # 2 req/sec, max 2 burst

    # Acquire multiple tokens rapidly
    start = asyncio.get_event_loop().time()

    for _ in range(4):  # 4 requests with 2 burst capacity
        await limiter.acquire()

    elapsed = asyncio.get_event_loop().time() - start

    # Should take at least 0.5 sec for 4 requests at 2/sec w/ 2 burst
    # (2 burst instant + 2 more = 1 sec wait)
    assert elapsed >= 0.5


@pytest.mark.asyncio
async def test_rate_limiter_burst_capacity():
    """Test burst capacity handling."""
    limiter = RateLimiter(requests_per_minute=60.0, burst_capacity=5)

    # Should handle burst quickly
    start = asyncio.get_event_loop().time()

    for _ in range(5):
        await limiter.acquire()

    elapsed = asyncio.get_event_loop().time() - start

    # Burst should be fast (within capacity)
    assert elapsed < 1.0


@pytest.mark.asyncio
async def test_rate_limiter_try_acquire():
    """Test non-blocking acquire."""
    limiter = RateLimiter(requests_per_minute=60.0, burst_capacity=2)

    # First two should succeed
    assert await limiter.try_acquire()
    assert await limiter.try_acquire()

    # Third should fail (burst depleted)
    assert not await limiter.try_acquire()


@pytest.mark.asyncio
async def test_rate_limiter_set_rate():
    """Test dynamic rate limit change."""
    limiter = RateLimiter(requests_per_minute=60.0)

    assert limiter.rate == 1.0  # 1 per second

    limiter.set_rate(120.0)
    assert limiter.rate == 2.0  # 2 per second


@pytest.mark.asyncio
async def test_rate_limiter_reset():
    """Test limiter reset."""
    limiter = RateLimiter(requests_per_minute=60.0, burst_capacity=2)

    # Deplete tokens
    await limiter.acquire()
    await limiter.acquire()

    # Reset should restore capacity
    await limiter.reset()

    # Should acquire immediately
    success = await limiter.try_acquire()
    assert success


# ── MultiRateLimiter Tests


def test_multi_rate_limiter_add():
    """Test adding multiple limiters."""
    multi = MultiRateLimiter()

    limiter1 = multi.add_limiter("api1", 60.0)
    limiter2 = multi.add_limiter("api2", 120.0)

    assert limiter1 is not None
    assert limiter2 is not None
    assert multi.get_limiter("api1") == limiter1
    assert multi.get_limiter("api2") == limiter2


@pytest.mark.asyncio
async def test_multi_rate_limiter_acquire():
    """Test acquiring from named limiter."""
    multi = MultiRateLimiter()
    multi.add_limiter("test", 60.0)

    # Should acquire successfully
    await multi.acquire("test")


@pytest.mark.asyncio
async def test_multi_rate_limiter_acquire_nonexistent():
    """Test acquiring from non-existent limiter raises error."""
    multi = MultiRateLimiter()

    with pytest.raises(KeyError):
        await multi.acquire("nonexistent")


# ── FileWorker Tests


@pytest.mark.asyncio
async def test_file_worker_success():
    """Test successful file processing."""
    limiter = RateLimiter(requests_per_minute=60.0)
    worker = FileWorker(
        rate_limiter=limiter, max_retries=3, skip_validation=True
    )

    # Mock the process_file function
    with patch("ingest.ingest.process_file") as mock:
        mock.return_value = (10, "ok")

        file_path = Path("/test/file.txt")
        docs_root = Path("/test")

        result = await worker.process_file(
            file_path=file_path,
            docs_root=docs_root,
            store=MagicMock(),
            registry=MagicMock(),
        )

        assert result.success
        assert result.chunks_generated == 10
        assert result.status == "ok"
        assert result.retries == 0


@pytest.mark.asyncio
async def test_file_worker_retry():
    """Test retry logic on failure."""
    worker = FileWorker(rate_limiter=None, max_retries=2, skip_validation=True)

    # Mock to fail twice then succeed
    with patch("ingest.ingest.process_file") as mock:
        mock.side_effect = [
            Exception("Fail 1"),
            Exception("Fail 2"),
            (5, "ok"),
        ]

        file_path = Path("/test/file.txt")
        result = await worker.process_file(
            file_path=file_path,
            docs_root=Path("/test"),
            store=MagicMock(),
            registry=MagicMock(),
        )

        assert result.success
        assert result.retries == 2
        assert mock.call_count == 3


@pytest.mark.asyncio
async def test_file_worker_max_retries():
    """Test exceeding max retries."""
    worker = FileWorker(rate_limiter=None, max_retries=2, skip_validation=True)

    # Mock to always fail
    with patch("ingest.ingest.process_file") as mock:
        mock.side_effect = Exception("Persistent error")

        result = await worker.process_file(
            file_path=Path("/test/file.txt"),
            docs_root=Path("/test"),
            store=MagicMock(),
            registry=MagicMock(),
        )

        assert not result.success
        assert result.status == "error"
        assert result.retries == 3  # Initial + 2 retries
        assert mock.call_count == 3


# ── WorkerStats Tests


def test_worker_stats_record_success():
    """Test recording successful result."""
    stats = WorkerStats()

    result = WorkerResult(
        file_path=Path("/test/file.txt"),
        success=True,
        chunks_generated=10,
        status="ok",
    )

    stats.record_result(result)

    assert stats.files_processed == 1
    assert stats.chunks_generated == 10
    assert stats.files_failed == 0


def test_worker_stats_record_skipped():
    """Test recording skipped file."""
    stats = WorkerStats()

    result = WorkerResult(
        file_path=Path("/test/file.txt"),
        success=True,
        status="skipped",
    )

    stats.record_result(result)

    assert stats.files_skipped == 1
    assert stats.files_processed == 0


def test_worker_stats_record_failed():
    """Test recording failed file."""
    stats = WorkerStats()

    result = WorkerResult(
        file_path=Path("/test/file.txt"),
        success=False,
        error="Test error",
        status="error",
    )

    stats.record_result(result)

    assert stats.files_failed == 1
    assert stats.files_processed == 0


def test_worker_stats_summary():
    """Test stats summary."""
    stats = WorkerStats()

    # Add various results
    stats.record_result(
        WorkerResult(Path("/test/1.txt"), True, 10, status="ok")
    )
    stats.record_result(
        WorkerResult(Path("/test/2.txt"), True, status="skipped")
    )
    stats.record_result(
        WorkerResult(Path("/test/3.txt"), False, status="error")
    )

    summary = stats.summary()

    assert summary["processed"] == 1
    assert summary["skipped"] == 1
    assert summary["failed"] == 1
    assert summary["chunks"] == 10
    assert summary["total"] == 3


# ── WorkerPool Tests


@pytest.mark.asyncio
async def test_worker_pool_start_stop():
    """Test starting and stopping worker pool."""
    pool = WorkerPool(num_workers=2, skip_validation=True)

    assert not pool.is_running()

    await pool.start()
    assert pool.is_running()
    assert len(pool.workers) == 2

    await pool.stop()
    assert not pool.is_running()
    assert len(pool.workers) == 0


@pytest.mark.asyncio
async def test_worker_pool_context_manager():
    """Test pool as async context manager."""
    async with WorkerPool(num_workers=2, skip_validation=True) as pool:
        assert pool.is_running()

    assert not pool.is_running()


@pytest.mark.asyncio
async def test_worker_pool_submit_task():
    """Test submitting task to pool."""
    pool = WorkerPool(num_workers=1, max_queue_size=10, skip_validation=True)
    await pool.start()

    task = WorkerTask(
        file_path=Path("/test/file.txt"),
        docs_root=Path("/test"),
        store=MagicMock(),
        registry=MagicMock(),
    )

    await pool.submit(task)
    assert pool.queue_size() >= 0  # Task may already be processing

    await pool.stop()


@pytest.mark.asyncio
async def test_worker_pool_get_result():
    """Test getting result from pool."""
    pool = WorkerPool(num_workers=1, skip_validation=True)
    await pool.start()

    # Mock worker processing
    with patch("ingest.ingest.process_file") as mock:
        mock.return_value = (5, "ok")

        task = WorkerTask(
            file_path=Path("/test/file.txt"),
            docs_root=Path("/test"),
            store=MagicMock(),
            registry=MagicMock(),
        )

        await pool.submit(task)

        result = await pool.get_result(timeout=5.0)
        assert result is not None
        assert result.success

    await pool.stop()


@pytest.mark.asyncio
async def test_worker_pool_result_timeout():
    """Test result timeout."""
    pool = WorkerPool(num_workers=1, skip_validation=True)
    await pool.start()

    # Don't submit any tasks
    result = await pool.get_result(timeout=0.1)
    assert result is None

    await pool.stop()


@pytest.mark.asyncio
async def test_worker_pool_batch_submit():
    """Test submitting batch of tasks."""
    pool = WorkerPool(num_workers=2, skip_validation=True)
    await pool.start()

    tasks = [
        WorkerTask(
            Path(f"/test/file{i}.txt"),
            Path("/test"),
            MagicMock(),
            MagicMock(),
        )
        for i in range(5)
    ]

    with patch("ingest.ingest.process_file") as mock:
        mock.return_value = (1, "ok")
        await pool.submit_batch(tasks)

        # Get all results
        results = await pool.get_all_results(expected_count=5, timeout=10.0)

        assert len(results) == 5

    await pool.stop()


# ── Integration Tests


@pytest.mark.asyncio
async def test_worker_pool_with_rate_limiter():
    """Test worker pool with rate limiting."""
    limiter = RateLimiter(
        requests_per_minute=120.0, burst_capacity=2
    )  # 2/sec, 2 burst
    pool = WorkerPool(
        num_workers=2, rate_limiter=limiter, skip_validation=True
    )

    await pool.start()

    with patch("ingest.ingest.process_file") as mock:
        mock.return_value = (1, "ok")

        tasks = [
            WorkerTask(
                Path(f"/test/file{i}.txt"),
                Path("/test"),
                MagicMock(),
                MagicMock(),
            )
            for i in range(5)  # 5 tasks to exceed burst
        ]

        start = asyncio.get_event_loop().time()
        await pool.submit_batch(tasks)

        results = await pool.get_all_results(expected_count=5, timeout=10.0)
        elapsed = asyncio.get_event_loop().time() - start

        assert len(results) == 5

        # With 2 req/sec limit and 2 burst, 5 requests should take >=
        #  1 second (2 burst + 3 more at 2/sec = 1.5s minimum)
        assert elapsed >= 1.0

    await pool.stop()
