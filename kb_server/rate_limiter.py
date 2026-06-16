"""
Per-subject token bucket rate limiter for server request handling.

Wraps ingest/worker/limiter.RateLimiter to provide per-subject
tracking with auto-creation and periodic stale cleanup. Designed
for the request choke points in kb_server/server.py.
"""

import asyncio
import logging
import time
from typing import Optional

from ingest.worker.limiter import RateLimiter

log = logging.getLogger("kb-mcp.rate_limiter")


class ServerRateLimiter:
    """Per-subject token bucket rate limiter.

    Manages a dict of RateLimiter instances keyed by subject
    (API key prefix, IP address, etc.). Auto-creates on first
    check and periodically cleans up idle subjects.

    Attributes:
        requests_per_minute: Default rate for new subjects.
        burst_capacity: Default burst capacity (None = 2x rate).
        cleanup_interval: Seconds between idle-subject sweeps.
    """

    def __init__(
        self,
        requests_per_minute: float = 100.0,
        burst_capacity: Optional[int] = None,
        cleanup_interval: int = 300,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.burst_capacity = burst_capacity
        self.cleanup_interval = cleanup_interval
        self._limiters: dict[str, RateLimiter] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup = time.monotonic()

    async def _get_limiter(self, subject: str) -> RateLimiter:
        """Return existing or newly created limiter for *subject*."""
        limiter = self._limiters.get(subject)
        if limiter is not None:
            return limiter
        async with self._lock:
            # Double-check after acquiring lock
            limiter = self._limiters.get(subject)
            if limiter is None:
                limiter = RateLimiter(
                    requests_per_minute=self.requests_per_minute,
                    burst_capacity=self.burst_capacity,
                )
                self._limiters[subject] = limiter
                log.debug("Created rate limiter for subject=%s", subject)
            return limiter

    async def check(self, subject: str) -> tuple[bool, int]:
        """Check whether a request from *subject* is allowed.

        Returns:
            (allowed, retry_after_seconds):
            - (True, 0) if the request may proceed.
            - (False, n) if the request should be rejected with a
              ``Retry-After`` of *n* seconds.
        """
        await self._maybe_cleanup()
        limiter = await self._get_limiter(subject)

        allowed = await limiter.try_acquire()
        if allowed:
            return True, 0

        # Compute approximate wait until next token is available.
        available = limiter.available_tokens()
        wait = (
            max(1, int((1.0 - available) / limiter.rate))
            if available < 1
            else 1
        )
        return False, wait

    async def subject_count(self) -> int:
        """Number of currently tracked subjects."""
        return len(self._limiters)

    async def _maybe_cleanup(self) -> None:
        """Periodically sweep idle limiters."""
        now = time.monotonic()
        if now - self._last_cleanup < self.cleanup_interval:
            return
        self._last_cleanup = now
        # There is no idle-tracking on the inner RateLimiter, so for
        # now we only clean up subjects that have full token buckets
        # (indicating no recent activity).  A production deployment
        # that needs tighter bounds should add a last-access timestamp.
        async with self._lock:
            idle = [
                subj
                for subj, lim in self._limiters.items()
                if lim.available_tokens() >= lim.capacity
            ]
            for subj in idle:
                del self._limiters[subj]
            if idle:
                log.debug("Cleaned up %d idle rate-limit subjects", len(idle))
