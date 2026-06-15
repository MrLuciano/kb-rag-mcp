import bisect
import logging
from typing import Optional

log = logging.getLogger("kb-mcp.percentiles")

_DEFAULT_WINDOW_SIZE = 1000
_PERCENTILES = [50, 95, 99]


class PercentileTracker:
    """Bounded-memory sorted-list percentile tracker per operation.

    Records latency samples per operation key. Samples are stored in
    sorted lists bounded by ``window_size``. Provides p50/p95/p99
    statistics and Prometheus export.
    """

    def __init__(self, window_size: int = _DEFAULT_WINDOW_SIZE):
        self._window_size = window_size
        self._data: dict[str, list[float]] = {}

    def record(self, operation: str, latency_ms: float) -> None:
        """Record a latency sample for the given operation."""
        if operation not in self._data:
            self._data[operation] = []
        samples = self._data[operation]
        bisect.insort(samples, latency_ms)
        if len(samples) > self._window_size:
            samples.pop(0)

    def get_stats(self, operation: str) -> dict:
        """Return count, p50, p95, p99 for an operation."""
        samples = self._data.get(operation, [])
        if not samples:
            return {
                "count": 0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }
        n = len(samples)
        return {
            "count": n,
            "p50": _percentile(samples, 50),
            "p95": _percentile(samples, 95),
            "p99": _percentile(samples, 99),
        }

    def get_all_stats(self) -> dict[str, dict]:
        """Return stats for all tracked operations."""
        return {op: self.get_stats(op) for op in self._data}

    def reset(self) -> None:
        """Clear all samples."""
        self._data.clear()

    def export_prometheus(self) -> str:
        """Generate Prometheus gauge lines and reset data.

        Returns:
            Prometheus text format lines for percentile metrics.
        """
        lines: list[str] = []
        for op in list(self._data.keys()):
            stats = self.get_stats(op)
            if stats["count"] == 0:
                continue
            for p in _PERCENTILES:
                key = f"p{p}".lower()
                lines.append(
                    f'kb_rag_latency_ms{{operation="{op}",'
                    f'percentile="{p}"}} {stats[key]}'
                )
        self.reset()
        return "\n".join(lines)


def _percentile(sorted_samples: list[float], p: int) -> float:
    """Compute the p-th percentile from a sorted list."""
    if not sorted_samples:
        return 0.0
    k = (p / 100.0) * (len(sorted_samples) - 1)
    f = int(k)
    c = f + 1
    if c >= len(sorted_samples):
        return sorted_samples[-1]
    return sorted_samples[f] + (k - f) * (
        sorted_samples[c] - sorted_samples[f]
    )


# Module-level singleton
_tracker: Optional[PercentileTracker] = None


def get_percentile_tracker() -> PercentileTracker:
    """Get or create the singleton PercentileTracker."""
    global _tracker
    if _tracker is None:
        _tracker = PercentileTracker()
    return _tracker
