"""Unit tests for observability/metrics.py — Prometheus metric helpers.

FASE 12/14/17: Covers query metrics, batch metrics, and cache metrics
added during recent metrics-wiring work.
"""
import time
from unittest.mock import MagicMock, patch

import pytest
from prometheus_client import REGISTRY

from observability import metrics as m


# ── Helpers ──────────────────────────────────────────────────────────────────

def _clear_metric(metric_name: str) -> None:
    """Remove a metric from the global registry so tests don't collide."""
    collectors = list(REGISTRY._collector_to_names.keys())
    for c in collectors:
        names = REGISTRY._collector_to_names.get(c, set())
        if metric_name in names:
            REGISTRY.unregister(c)


# ── Query Metrics ────────────────────────────────────────────────────────────


class TestRecordQuery:
    def test_record_query_success(self):
        _clear_metric("kb_rag_query_duration_seconds")
        m.query_duration = m.Histogram(
            "kb_rag_query_duration_seconds",
            "Query duration",
            ["tool", "status"],
            buckets=[0.01, 0.1, 1.0, 5.0],
        )
        m.record_query("search_kb", "success", 0.05)
        # Metric observed — no exception is the primary assertion

    def test_record_query_error(self):
        _clear_metric("kb_rag_query_errors_total")
        m.query_errors = m.Counter(
            "kb_rag_query_errors_total",
            "Query errors",
            ["tool"],
        )
        m.record_query_error("search_kb")


# ── Batch Metrics ──────────────────────────────────────────────────────────


class TestRecordBatchEmbedding:
    def test_small_batch(self):
        _clear_metric("kb_batch_embeddings_total")
        _clear_metric("kb_batch_embedding_texts_total")
        _clear_metric("kb_batch_embedding_duration_seconds")
        m.batch_embeddings_total = m.Counter(
            "kb_batch_embeddings_total", "", ["backend", "batch_size_range"]
        )
        m.batch_embedding_texts = m.Counter(
            "kb_batch_embedding_texts_total", "", ["backend"]
        )
        m.batch_embedding_duration = m.Histogram(
            "kb_batch_embedding_duration_seconds", "",
            buckets=[0.1, 0.5, 1.0],
        )
        m.record_batch_embedding("openai-compat", 5, 0.3)

    def test_medium_batch(self):
        _clear_metric("kb_batch_embeddings_total")
        _clear_metric("kb_batch_embedding_texts_total")
        _clear_metric("kb_batch_embedding_duration_seconds")
        m.batch_embeddings_total = m.Counter(
            "kb_batch_embeddings_total", "", ["backend", "batch_size_range"]
        )
        m.batch_embedding_texts = m.Counter(
            "kb_batch_embedding_texts_total", "", ["backend"]
        )
        m.batch_embedding_duration = m.Histogram(
            "kb_batch_embedding_duration_seconds", "",
            buckets=[0.1, 0.5, 1.0],
        )
        m.record_batch_embedding("ollama", 25, 1.5)

    def test_large_batch(self):
        _clear_metric("kb_batch_embeddings_total")
        _clear_metric("kb_batch_embedding_texts_total")
        _clear_metric("kb_batch_embedding_duration_seconds")
        m.batch_embeddings_total = m.Counter(
            "kb_batch_embeddings_total", "", ["backend", "batch_size_range"]
        )
        m.batch_embedding_texts = m.Counter(
            "kb_batch_embedding_texts_total", "", ["backend"]
        )
        m.batch_embedding_duration = m.Histogram(
            "kb_batch_embedding_duration_seconds", "",
            buckets=[0.1, 0.5, 1.0],
        )
        m.record_batch_embedding("lmstudio-rest", 100, 5.0)


class TestRecordBatchUpsert:
    def test_sequential_upsert(self):
        _clear_metric("kb_batch_upserts_total")
        _clear_metric("kb_batch_upsert_points_total")
        _clear_metric("kb_batch_upsert_duration_seconds")
        m.batch_upserts_total = m.Counter(
            "kb_batch_upserts_total", "", ["parallel"]
        )
        m.batch_upsert_points = m.Counter(
            "kb_batch_upsert_points_total", "",
        )
        m.batch_upsert_duration = m.Histogram(
            "kb_batch_upsert_duration_seconds", "",
            buckets=[0.1, 0.5, 1.0],
        )
        m.record_batch_upsert(50, 2.0, parallel=False)

    def test_parallel_upsert(self):
        _clear_metric("kb_batch_upserts_total")
        _clear_metric("kb_batch_upsert_points_total")
        _clear_metric("kb_batch_upsert_duration_seconds")
        m.batch_upserts_total = m.Counter(
            "kb_batch_upserts_total", "", ["parallel"]
        )
        m.batch_upsert_points = m.Counter(
            "kb_batch_upsert_points_total", "",
        )
        m.batch_upsert_duration = m.Histogram(
            "kb_batch_upsert_duration_seconds", "",
            buckets=[0.1, 0.5, 1.0],
        )
        m.record_batch_upsert(200, 3.0, parallel=True)


# ── Cache Metrics ────────────────────────────────────────────────────────────


class TestUpdateCacheMetrics:
    def test_update_cache_metrics(self):
        _clear_metric("kb_cache_size_bytes")
        _clear_metric("kb_cache_entries")
        m.cache_size_bytes = m.Gauge(
            "kb_cache_size_bytes", "", ["backend"]
        )
        m.cache_entries = m.Gauge(
            "kb_cache_entries", "", ["backend"]
        )
        m.update_cache_metrics("lru", 1024, 42)


# ── MetricsCollector ─────────────────────────────────────────────────────────


class TestMetricsCollector:
    def test_init_has_all_attributes(self):
        collector = m.MetricsCollector()
        assert hasattr(collector, "jobs_created")
        assert hasattr(collector, "query_duration")
        assert hasattr(collector, "query_errors")
        assert hasattr(collector, "batch_embeddings_total")
        assert hasattr(collector, "batch_upserts_total")

    def test_increment_counter_with_labels(self):
        _clear_metric("kb_cache_hits_total")
        m.cache_hits = m.Counter("kb_cache_hits_total", "", ["backend"])
        collector = m.MetricsCollector()
        collector.increment("cache_hits", 1, backend="lru")

    def test_increment_counter_without_labels(self):
        _clear_metric("kb_batch_upsert_points_total")
        m.batch_upsert_points = m.Counter("kb_batch_upsert_points_total", "")
        collector = m.MetricsCollector()
        collector.increment("batch_upsert_points", 5)

    def test_increment_missing_metric_noop(self):
        collector = m.MetricsCollector()
        # Should not raise
        collector.increment("nonexistent_metric")


# ── Server Integration ───────────────────────────────────────────────────────


class TestServerMetricsIntegration:
    """Verify kb_server/server.py call_tool() invokes metric helpers."""

    @pytest.mark.asyncio
    async def test_call_tool_records_query_on_success(self):
        import kb_server.server as srv
        with patch.object(srv, "record_query") as mock_rq:
            with patch.object(srv, "_list_collections", return_value=[]):
                await srv.call_tool("list_collections", {})
        mock_rq.assert_called_once()
        args = mock_rq.call_args[0]
        assert args[0] == "list_collections"
        assert args[1] == "success"
        assert isinstance(args[2], float)

    @pytest.mark.asyncio
    async def test_call_tool_records_query_error_on_exception(self):
        import kb_server.server as srv
        with patch.object(srv, "record_query") as mock_rq:
            with patch.object(srv, "record_query_error") as mock_err:
                with patch.object(
                    srv, "_search_kb", side_effect=RuntimeError("boom")
                ):
                    result = await srv.call_tool("search_kb", {"query": "x"})
        mock_rq.assert_called_once()
        mock_err.assert_called_once_with("search_kb")
        assert any("boom" in r.text for r in result)

    @pytest.mark.asyncio
    async def test_call_tool_records_query_for_list_filter_options(self):
        import kb_server.server as srv
        with patch.object(srv, "record_query") as mock_rq:
            with patch.object(
                srv, "_list_filter_options", return_value=[]
            ):
                await srv.call_tool("list_filter_options", {})
        mock_rq.assert_called_once()
        assert mock_rq.call_args[0][0] == "list_filter_options"


# ── Prometheus Export ────────────────────────────────────────────────────────


class TestGetMetrics:
    def test_returns_bytes_and_content_type(self):
        data, ctype = m.get_metrics()
        assert isinstance(data, bytes)
        assert ctype == "text/plain; version=1.0.0; charset=utf-8"
