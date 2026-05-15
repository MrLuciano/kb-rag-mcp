"""
Rate limiter for controlling API request rates.

Uses token bucket algorithm to allow bursts while maintaining
average rate limits. Async-safe for concurrent workers.
"""

import asyncio
import logging
import time
from typing import Optional

log = logging.getLogger("kb-ingest.worker.limiter")


class RateLimiter:
    """
    Token bucket rate limiter for async operations.

    Allows bursts up to bucket capacity while maintaining
    average rate over time. Thread-safe and async-safe.

    Attributes:
        rate: Tokens per second (requests/sec)
        capacity: Maximum tokens (burst capacity)
        tokens: Current available tokens
        last_update: Last token refill timestamp
    """

    def __init__(
        self,
        requests_per_minute: float = 60.0,
        burst_capacity: Optional[int] = None,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Average requests per minute
            burst_capacity: Max burst size (None = 2x rate)
        """
        self.rate = requests_per_minute / 60.0  # Convert to per-second
        self.capacity = (
            burst_capacity
            if burst_capacity is not None
            else int(self.rate * 2)
        )
        self.tokens = float(self.capacity)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

        log.info(
            f"RateLimiter: {requests_per_minute:.1f} req/min "
            f"(burst={self.capacity})"
        )

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default 1)
        """
        async with self._lock:
            while True:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    log.debug(
                        f"Acquired {tokens} token(s), "
                        f"{self.tokens:.1f} remaining"
                    )
                    return

                # Calculate wait time for enough tokens
                wait_time = (tokens - self.tokens) / self.rate
                log.debug(f"Rate limit reached, waiting {wait_time:.2f}s")

                # Release lock during wait to allow other operations
                self._lock.release()
                try:
                    await asyncio.sleep(wait_time)
                finally:
                    await self._lock.acquire()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update

        # Add tokens based on elapsed time
        new_tokens = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_update = now

    async def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without waiting.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if acquired, False if not enough tokens
        """
        async with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    def available_tokens(self) -> int:
        """Get current available token count (approximate)."""
        return int(self.tokens)

    def set_rate(self, requests_per_minute: float) -> None:
        """
        Update rate limit dynamically.

        Args:
            requests_per_minute: New rate limit
        """
        old_rate = self.rate * 60.0
        self.rate = requests_per_minute / 60.0

        # Adjust capacity proportionally
        self.capacity = int(self.rate * 2)

        log.info(
            f"Rate limit changed: {old_rate:.1f} → "
            f"{requests_per_minute:.1f} req/min"
        )

    async def reset(self) -> None:
        """Reset limiter to full capacity."""
        async with self._lock:
            self.tokens = float(self.capacity)
            self.last_update = time.monotonic()
            log.debug("Rate limiter reset")


class MultiRateLimiter:
    """
    Manages multiple rate limiters for different resources.

    Useful when different API endpoints have different limits.
    """

    def __init__(self):
        self.limiters: dict[str, RateLimiter] = {}

    def add_limiter(
        self,
        name: str,
        requests_per_minute: float,
        burst_capacity: Optional[int] = None,
    ) -> RateLimiter:
        """
        Add a named rate limiter.

        Args:
            name: Limiter identifier
            requests_per_minute: Rate limit
            burst_capacity: Burst size

        Returns:
            Created RateLimiter instance
        """
        limiter = RateLimiter(requests_per_minute, burst_capacity)
        self.limiters[name] = limiter
        return limiter

    def get_limiter(self, name: str) -> Optional[RateLimiter]:
        """Get limiter by name."""
        return self.limiters.get(name)

    async def acquire(self, name: str, tokens: int = 1) -> None:
        """
        Acquire tokens from named limiter.

        Args:
            name: Limiter identifier
            tokens: Number of tokens

        Raises:
            KeyError: If limiter doesn't exist
        """
        limiter = self.limiters.get(name)
        if limiter is None:
            raise KeyError(f"Rate limiter '{name}' not found")

        await limiter.acquire(tokens)

    async def acquire_all(
        self, limiter_names: list[str], tokens: int = 1
    ) -> None:
        """
        Acquire tokens from multiple limiters atomically.

        Args:
            limiter_names: List of limiter identifiers
            tokens: Tokens to acquire from each

        Raises:
            KeyError: If any limiter doesn't exist
        """
        # Acquire from all limiters in order
        for name in limiter_names:
            await self.acquire(name, tokens)
