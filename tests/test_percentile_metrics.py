from kb_server.observability.percentiles import (
    PercentileTracker,
    get_percentile_tracker,
)


class TestPercentileTracker:
    def test_record_and_get_stats(self):
        tracker = PercentileTracker(window_size=100)
        tracker.record("search_kb", 10.0)
        tracker.record("search_kb", 20.0)
        tracker.record("search_kb", 30.0)
        stats = tracker.get_stats("search_kb")
        assert stats["count"] == 3
        assert stats["p50"] == 20.0
        assert stats["p99"] == 29.8

    def test_empty_operation(self):
        tracker = PercentileTracker()
        stats = tracker.get_stats("nonexistent")
        assert stats["count"] == 0
        assert stats["p50"] == 0.0
        assert stats["p95"] == 0.0
        assert stats["p99"] == 0.0

    def test_window_size_bounds_memory(self):
        tracker = PercentileTracker(window_size=5)
        for i in range(20):
            tracker.record("op", float(i))
        stats = tracker.get_stats("op")
        assert stats["count"] == 5
        # Most recent values kept (largest after insort)
        assert stats["p50"] > 10.0

    def test_reset(self):
        tracker = PercentileTracker()
        tracker.record("op", 42.0)
        assert tracker.get_stats("op")["count"] == 1
        tracker.reset()
        assert tracker.get_stats("op")["count"] == 0

    def test_export_prometheus(self):
        tracker = PercentileTracker()
        tracker.record("search_kb", 10.0)
        tracker.record("search_kb", 50.0)
        tracker.record("search_kb", 100.0)

        output = tracker.export_prometheus()
        assert "kb_rag_latency_ms" in output
        assert 'operation="search_kb"' in output
        assert 'percentile="50"' in output
        assert 'percentile="95"' in output
        assert 'percentile="99"' in output

        # Data reset after export
        assert tracker.get_stats("search_kb")["count"] == 0

    def test_get_all_stats(self):
        tracker = PercentileTracker()
        tracker.record("op1", 10.0)
        tracker.record("op2", 20.0)
        all_stats = tracker.get_all_stats()
        assert "op1" in all_stats
        assert "op2" in all_stats

    def test_singleton(self):
        t1 = get_percentile_tracker()
        t2 = get_percentile_tracker()
        assert t1 is t2
