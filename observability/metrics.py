"""
Prometheus metrics for KB ingestion system.

Provides metrics for monitoring jobs, workers, and ingestion pipeline.
"""

from typing import Dict

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# ── Metrics Collector ────────────────────────────────────────────


class MetricsCollector:
    """Container for all metrics - simplifies passing to components."""

    def __init__(self) -> None:
        """Initialize with references to all module-level metrics."""
        # Job metrics
        self.jobs_created = jobs_created
        self.jobs_completed = jobs_completed
        self.jobs_active = jobs_active
        self.job_duration = job_duration
        # File metrics
        self.files_processed = files_processed
        self.files_processing_time = files_processing_time
        self.chunks_generated = chunks_generated
        # Worker metrics
        self.worker_pool_size = worker_pool_size
        self.worker_pool_queue_size = worker_pool_queue_size
        self.worker_pool_utilization = worker_pool_utilization
        # Rate limiter metrics
        self.rate_limiter_tokens = rate_limiter_tokens
        self.rate_limiter_waits = rate_limiter_waits
        self.rate_limiter_wait_time = rate_limiter_wait_time
        # API metrics
        self.api_requests = api_requests
        self.api_latency = api_latency
        # Cache metrics
        self.cache_hits = cache_hits
        self.cache_misses = cache_misses
        self.cache_evictions = cache_evictions
        self.cache_size_bytes = cache_size_bytes
        self.cache_entries = cache_entries
        # FASE 8: Batch metrics
        self.batch_embeddings_total = batch_embeddings_total
        self.batch_embedding_texts = batch_embedding_texts
        self.batch_embedding_duration = batch_embedding_duration
        self.batch_upserts_total = batch_upserts_total
        self.batch_upsert_points = batch_upsert_points
        self.batch_upsert_duration = batch_upsert_duration
        self.http_pool_connections = http_pool_connections
        self.batch_processing_throughput = batch_processing_throughput
    
    def increment(self, metric_name: str, value: int = 1, **labels) -> None:
        """Helper to increment counter metrics."""
        metric = getattr(self, metric_name, None)
        if metric and hasattr(metric, "labels"):
            if labels:
                metric.labels(**labels).inc(value)
            else:
                metric.inc(value)


# ── Job Metrics ──────────────────────────────────────────────────


jobs_created = Counter(
    "kb_ingest_jobs_created_total",
    "Total number of jobs created",
    ["priority"],
)

jobs_completed = Counter(
    "kb_ingest_jobs_completed_total",
    "Total number of jobs completed",
    ["status"],  # completed, failed, cancelled
)

jobs_active = Gauge(
    "kb_ingest_jobs_active",
    "Number of currently active jobs",
    ["status"],  # pending, running, paused
)

job_duration = Histogram(
    "kb_ingest_job_duration_seconds",
    "Job execution duration in seconds",
    buckets=[10, 30, 60, 300, 600, 1800, 3600],
)


# ── File Processing Metrics ──────────────────────────────────────


files_processed = Counter(
    "kb_ingest_files_processed_total",
    "Total number of files processed",
    ["status"],  # ok, skipped, error
)

files_processing_time = Histogram(
    "kb_ingest_file_processing_seconds",
    "File processing duration in seconds",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

chunks_generated = Counter(
    "kb_ingest_chunks_generated_total",
    "Total number of chunks generated",
    ["product", "doc_type"],
)


# ── Worker Pool Metrics ──────────────────────────────────────────


worker_pool_size = Gauge(
    "kb_ingest_worker_pool_size",
    "Number of workers in the pool",
)

worker_pool_queue_size = Gauge(
    "kb_ingest_worker_pool_queue_size",
    "Number of tasks in worker pool queue",
)

worker_pool_utilization = Gauge(
    "kb_ingest_worker_pool_utilization",
    "Worker pool utilization (0.0-1.0)",
)


# ── Rate Limiter Metrics ─────────────────────────────────────────


rate_limiter_tokens = Gauge(
    "kb_ingest_rate_limiter_tokens",
    "Available tokens in rate limiter",
    ["limiter"],
)

rate_limiter_waits = Counter(
    "kb_ingest_rate_limiter_waits_total",
    "Total number of rate limit waits",
    ["limiter"],
)

rate_limiter_wait_time = Histogram(
    "kb_ingest_rate_limiter_wait_seconds",
    "Time spent waiting for rate limiter",
    ["limiter"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)


# ── API Metrics ──────────────────────────────────────────────────


api_requests = Counter(
    "kb_ingest_api_requests_total",
    "Total number of API requests",
    ["endpoint", "status"],
)

api_latency = Histogram(
    "kb_ingest_api_latency_seconds",
    "API request latency in seconds",
    ["endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)


# ── Cache Metrics ────────────────────────────────────────────────


cache_hits = Counter(
    "kb_rag_cache_hits_total",
    "Total number of cache hits",
    ["backend"],  # lru, redis
)

cache_misses = Counter(
    "kb_rag_cache_misses_total",
    "Total number of cache misses",
    ["backend"],
)

cache_evictions = Counter(
    "kb_rag_cache_evictions_total",
    "Total number of cache evictions",
    ["backend", "reason"],  # size_limit, expired, manual, clear
)

cache_size_bytes = Gauge(
    "kb_rag_cache_size_bytes",
    "Current cache size in bytes",
    ["backend"],
)

cache_entries = Gauge(
    "kb_rag_cache_entries",
    "Number of entries in cache",
    ["backend"],
)


# ── Helper Functions ─────────────────────────────────────────────


def record_job_created(priority: str) -> None:
    """Record a job creation."""
    jobs_created.labels(priority=priority).inc()


def record_job_completed(status: str, duration: float) -> None:
    """
    Record job completion.

    Args:
        status: Job completion status (completed/failed/cancelled)
        duration: Job duration in seconds
    """
    jobs_completed.labels(status=status).inc()
    job_duration.observe(duration)


def update_active_jobs(counts: Dict[str, int]) -> None:
    """
    Update active job counts.

    Args:
        counts: Dict with status -> count mapping
    """
    for status in ["pending", "running", "paused"]:
        jobs_active.labels(status=status).set(counts.get(status, 0))


def record_file_processed(
    status: str, duration: float, chunks: int = 0
) -> None:
    """
    Record file processing.

    Args:
        status: Processing status (ok/skipped/error)
        duration: Processing duration in seconds
        chunks: Number of chunks generated
    """
    files_processed.labels(status=status).inc()
    if duration > 0:
        files_processing_time.observe(duration)


def record_chunks_generated(
    product: str, doc_type: str, count: int = 1
) -> None:
    """
    Record chunks generated.

    Args:
        product: Product name
        doc_type: Document type
        count: Number of chunks
    """
    chunks_generated.labels(product=product, doc_type=doc_type).inc(count)


def update_worker_pool_metrics(
    pool_size: int, queue_size: int, utilization: float
) -> None:
    """
    Update worker pool metrics.

    Args:
        pool_size: Number of workers
        queue_size: Queue size
        utilization: Pool utilization (0.0-1.0)
    """
    worker_pool_size.set(pool_size)
    worker_pool_queue_size.set(queue_size)
    worker_pool_utilization.set(utilization)


def update_rate_limiter_tokens(limiter: str, tokens: float) -> None:
    """
    Update rate limiter token count.

    Args:
        limiter: Limiter name
        tokens: Available tokens
    """
    rate_limiter_tokens.labels(limiter=limiter).set(tokens)


def record_rate_limiter_wait(limiter: str, wait_time: float) -> None:
    """
    Record rate limiter wait.

    Args:
        limiter: Limiter name
        wait_time: Wait time in seconds
    """
    rate_limiter_waits.labels(limiter=limiter).inc()
    rate_limiter_wait_time.labels(limiter=limiter).observe(wait_time)


def record_api_request(endpoint: str, status: str, latency: float) -> None:
    """
    Record API request.

    Args:
        endpoint: API endpoint
        status: HTTP status or "success"/"error"
        latency: Request latency in seconds
    """
    api_requests.labels(endpoint=endpoint, status=status).inc()
    api_latency.labels(endpoint=endpoint).observe(latency)


def update_cache_metrics(backend: str, size_bytes: int, entries: int) -> None:
    """
    Update cache size and entry metrics.

    Args:
        backend: Cache backend (lru/redis)
        size_bytes: Cache size in bytes
        entries: Number of entries
    """
    cache_size_bytes.labels(backend=backend).set(size_bytes)
    cache_entries.labels(backend=backend).set(entries)


def get_metrics() -> tuple[bytes, str]:
    """
    Get metrics in Prometheus format.

    Returns:
        Tuple of (metrics_bytes, content_type)
    """
    return generate_latest(), CONTENT_TYPE_LATEST


# ── FASE 8: Batch Processing Metrics ────────────────────────────────


batch_embeddings_total = Counter(
    "kb_batch_embeddings_total",
    "Total number of batch embedding operations",
    ["backend", "batch_size_range"],  # small/medium/large
)

batch_embedding_texts = Counter(
    "kb_batch_embedding_texts_total",
    "Total number of texts embedded in batch operations",
    ["backend"],
)

batch_embedding_duration = Histogram(
    "kb_batch_embedding_duration_seconds",
    "Batch embedding operation duration",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

batch_upserts_total = Counter(
    "kb_batch_upserts_total",
    "Total number of batch upsert operations to Qdrant",
    ["parallel"],  # true/false
)

batch_upsert_points = Counter(
    "kb_batch_upsert_points_total",
    "Total number of points upserted in batch operations",
)

batch_upsert_duration = Histogram(
    "kb_batch_upsert_duration_seconds",
    "Batch upsert operation duration",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

http_pool_connections = Gauge(
    "kb_http_pool_connections",
    "Number of HTTP connections in pool",
    ["state"],  # idle/active
)

batch_processing_throughput = Gauge(
    "kb_batch_processing_throughput_chunks_per_sec",
    "Current batch processing throughput",
)


def record_batch_embedding(
    backend: str,
    num_texts: int,
    duration: float,
) -> None:
    """
    Record batch embedding operation.
    
    Args:
        backend: Embedding backend (openai-compat, ollama, etc)
        num_texts: Number of texts in batch
        duration: Operation duration in seconds
    """
    # Categorize batch size
    if num_texts < 10:
        size_range = "small"
    elif num_texts < 50:
        size_range = "medium"
    else:
        size_range = "large"
    
    batch_embeddings_total.labels(
        backend=backend, batch_size_range=size_range
    ).inc()
    batch_embedding_texts.labels(backend=backend).inc(num_texts)
    batch_embedding_duration.observe(duration)


def record_batch_upsert(
    num_points: int,
    duration: float,
    parallel: bool = False,
) -> None:
    """
    Record batch upsert operation.
    
    Args:
        num_points: Number of points upserted
        duration: Operation duration in seconds
        parallel: Whether parallel upsert was used
    """
    batch_upserts_total.labels(parallel=str(parallel).lower()).inc()
    batch_upsert_points.inc(num_points)
    batch_upsert_duration.observe(duration)


def update_http_pool_metrics(idle: int, active: int) -> None:
    """
    Update HTTP connection pool metrics.
    
    Args:
        idle: Number of idle connections
        active: Number of active connections
    """
    http_pool_connections.labels(state="idle").set(idle)
    http_pool_connections.labels(state="active").set(active)


def update_batch_throughput(chunks_per_sec: float) -> None:
    """
    Update batch processing throughput gauge.
    
    Args:
        chunks_per_sec: Current throughput in chunks/second
    """
    batch_processing_throughput.set(chunks_per_sec)
