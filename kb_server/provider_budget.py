"""
Provider budget accounting for embedding backends.

Tracks per-provider request counts and optional token counts within
a sliding time window. Enables budget enforcement before dispatching
requests to a backend provider.

PHASE 36: Provider Budget & Circuit Breaker
"""

import logging
import time
from collections import defaultdict, deque
from typing import Optional

log = logging.getLogger("kb-mcp.provider_budget")


class ProviderBudget:
    """
    Per-provider sliding window budget tracker.

    Tracks request counts within a configurable time window (e.g. last
    60 seconds). Optionally tracks token usage if `token_field` is
    provided in recorded request data.

    The budget is enforced by checking whether the current request count
    and (optionally) token count are within configured limits before
    dispatching a request.

    Thread-safe for asyncio usage since all operations are in-memory
    and accessed from a single event loop.
    """

    def __init__(
        self,
        window_seconds: float = 60.0,
        max_requests: int = 100,
        max_tokens: Optional[int] = None,
    ) -> None:
        """
        Initialize provider budget.

        Args:
            window_seconds: Sliding window duration in seconds.
            max_requests: Maximum requests allowed in the window.
            max_tokens: Maximum tokens allowed in the window (optional).
        """
        self._window_seconds = window_seconds
        self._max_requests = max_requests
        self._max_tokens = max_tokens

        # Per-provider: provider_name -> deque of (timestamp, tokens)
        self._usage: Dict[str, deque] = defaultdict(deque)

    # ── Public API ────────────────────────────────────────────────

    def check_budget(self, provider: str) -> bool:
        """
        Check if a provider has budget remaining for a request.

        Purges expired entries from the sliding window before checking.
        Returns True if the provider is within budget limits.

        Args:
            provider: Provider name.

        Returns:
            True if request is within budget, False if over limit.
        """
        self._purge(provider)
        dq = self._usage.get(provider)
        if not dq:
            return True

        if len(dq) >= self._max_requests:
            return False

        if self._max_tokens is not None:
            total_tokens = sum(entry[1] for entry in dq if len(entry) > 1)
            if total_tokens >= self._max_tokens:
                return False

        return True

    def record_request(
        self, provider: str, tokens: Optional[int] = None
    ) -> None:
        """
        Record a request for a provider in the sliding window.

        Args:
            provider: Provider name.
            tokens: Optional token count for this request.
        """
        entry: tuple = (time.monotonic(),)
        if tokens is not None:
            entry = (time.monotonic(), tokens)
        self._usage[provider].append(entry)

    def get_usage(self, provider: str) -> dict:
        """
        Get current usage stats for a provider within the window.

        Args:
            provider: Provider name.

        Returns:
            Dict with request_count, limit, and optionally token_count
            and token_limit.
        """
        self._purge(provider)
        dq = self._usage.get(provider, deque())

        result: dict = {
            "request_count": len(dq),
            "request_limit": self._max_requests,
            "remaining": max(0, self._max_requests - len(dq)),
        }

        if self._max_tokens is not None:
            total_tokens = sum(
                entry[1] for entry in dq if len(entry) > 1
            )
            result["token_count"] = total_tokens
            result["token_limit"] = self._max_tokens
            result["tokens_remaining"] = max(
                0, self._max_tokens - total_tokens
            )

        return result

    def budget_remaining(self, provider: str) -> float:
        """
        Return remaining budget as a ratio (0.0 to 1.0).

        1.0 means no usage, 0.0 means budget exhausted.
        Based on request count; if max_tokens is set, uses the more
        restrictive of request and token ratios.

        Args:
            provider: Provider name.

        Returns:
            Budget ratio (0.0 = exhausted, 1.0 = full).
        """
        self._purge(provider)
        dq = self._usage.get(provider, deque())

        request_ratio = 1.0 - (len(dq) / self._max_requests)

        if self._max_tokens is not None and dq:
            total_tokens = sum(entry[1] for entry in dq if len(entry) > 1)
            token_ratio = 1.0 - (total_tokens / self._max_tokens)
            return max(0.0, min(request_ratio, token_ratio))

        return max(0.0, request_ratio)

    def reset_provider(self, provider: str) -> None:
        """
        Reset usage tracking for a specific provider.

        Args:
            provider: Provider name.
        """
        self._usage.pop(provider, None)

    def reset_all(self) -> None:
        """Reset usage tracking for all providers."""
        self._usage.clear()

    def _purge(self, provider: str) -> None:
        """
        Remove expired entries from the sliding window.

        Args:
            provider: Provider name.
        """
        dq = self._usage.get(provider)
        if not dq:
            return

        cutoff = time.monotonic() - self._window_seconds
        while dq and dq[0][0] < cutoff:
            dq.popleft()
