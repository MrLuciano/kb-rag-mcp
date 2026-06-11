"""
Circuit breaker state machine for embedding provider backends.

Provides per-provider circuit breaker with CLOSED, OPEN, and HALF_OPEN
states. Configurable failure thresholds, cooldown periods, and exponential
backoff on repeated failures.

PHASE 36: Provider Budget & Circuit Breaker
"""

import enum
import logging
import time
from typing import Dict, Optional

log = logging.getLogger("kb-mcp.circuit_breaker")


class CircuitState(enum.Enum):
    """Circuit breaker state."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Per-provider circuit breaker state machine.

    States:
        CLOSED   — Normal operation, requests pass through.
        OPEN     — Requests are rejected immediately (fast fail).
                  Transitions to HALF_OPEN after cooldown.
        HALF_OPEN — Allows a single test request. On success transitions
                   to CLOSED; on failure transitions back to OPEN.

    Cooldown uses exponential backoff, starting at `cooldown_base`
    and doubling on each consecutive OPEN cycle up to `cooldown_max`.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_base: float = 30.0,
        cooldown_max: float = 300.0,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Consecutive failures before OPEN.
            cooldown_base: Initial cooldown in seconds (doubles on repeat).
            cooldown_max: Maximum cooldown in seconds.
        """
        self._failure_threshold = failure_threshold
        self._cooldown_base = cooldown_base
        self._cooldown_max = cooldown_max

        # Per-provider state: provider_name -> dict
        self._state: Dict[str, dict] = {}

    # ── Public API ────────────────────────────────────────────────

    def check(self, provider: str) -> CircuitState:
        """
        Return the current circuit state for a provider.

        If the breaker is OPEN and the cooldown has expired, transitions
        to HALF_OPEN automatically. This is the safe entry point for
        callers to decide whether to attempt a request.

        Args:
            provider: Provider name (e.g. "openai-compat", "ollama").

        Returns:
            Current CircuitState after any automatic transition.
        """
        info = self._get_or_create(provider)
        now = time.monotonic()

        if info["state"] == CircuitState.OPEN:
            if now >= info["open_until"]:
                log.info(
                    "Circuit breaker HALF_OPEN for provider '%s' "
                    "(cooldown expired after %.1fs)",
                    provider,
                    info["open_until"] - info["opened_at"],
                )
                # Allow a test request
                info["state"] = CircuitState.HALF_OPEN
                info["test_request_allowed"] = True

        return info["state"]

    def record_success(self, provider: str) -> None:
        """
        Record a successful request for a provider.

        In CLOSED state: resets failure count.
        In HALF_OPEN state: transitions to CLOSED (circuit healed).

        Does NOT reset the exponential backoff multiplier — repeated
        failure cycles continue to escalate cooldown until the provider
        is explicitly reset via `reset()`.

        Args:
            provider: Provider name.
        """
        info = self._get_or_create(provider)

        if info["state"] == CircuitState.HALF_OPEN:
            log.info(
                "Circuit breaker CLOSED for provider '%s' "
                "(test request succeeded)",
                provider,
            )

        info["state"] = CircuitState.CLOSED
        info["consecutive_failures"] = 0
        info["test_request_allowed"] = False

    def record_failure(self, provider: str) -> CircuitState:
        """
        Record a failed request for a provider.

        If consecutive failures reach threshold, transitions to OPEN.
        In HALF_OPEN state: transitions back to OPEN (failed test).

        Args:
            provider: Provider name.

        Returns:
            New CircuitState after recording the failure.
        """
        info = self._get_or_create(provider)
        now = time.monotonic()
        info["consecutive_failures"] += 1

        # HALF_OPEN failure -> back to OPEN immediately
        if info["state"] == CircuitState.HALF_OPEN:
            cooldown = self._next_cooldown(provider)
            info["state"] = CircuitState.OPEN
            info["opened_at"] = now
            info["open_until"] = now + cooldown
            info["test_request_allowed"] = False
            log.warning(
                "Circuit breaker OPEN for provider '%s' "
                "(test request failed, cooldown=%.1fs)",
                provider,
                cooldown,
            )
            return CircuitState.OPEN

        # CLOSED failure: check threshold
        if info["consecutive_failures"] >= self._failure_threshold:
            cooldown = self._next_cooldown(provider)
            info["state"] = CircuitState.OPEN
            info["opened_at"] = now
            info["open_until"] = now + cooldown
            log.warning(
                "Circuit breaker OPEN for provider '%s' "
                "(%d consecutive failures, cooldown=%.1fs)",
                provider,
                info["consecutive_failures"],
                cooldown,
            )
            return CircuitState.OPEN

        return CircuitState.CLOSED

    def get_failure_count(self, provider: str) -> int:
        """
        Return the current consecutive failure count for a provider.

        Args:
            provider: Provider name.

        Returns:
            Number of consecutive failures.
        """
        return self._get_or_create(provider)["consecutive_failures"]

    def is_open(self, provider: str) -> bool:
        """
        Quick check if a provider's circuit is open.

        Args:
            provider: Provider name.

        Returns:
            True if the circuit is in OPEN state (after auto HALF_OPEN
            transition if cooldown expired).
        """
        return self.check(provider) == CircuitState.OPEN

    def is_half_open(self, provider: str) -> bool:
        """
        Quick check if a provider's circuit is half-open.

        Args:
            provider: Provider name.

        Returns:
            True if the circuit is in HALF_OPEN state.
        """
        return self.check(provider) == CircuitState.HALF_OPEN

    def reset(self, provider: str) -> None:
        """
        Reset circuit breaker state for a provider to CLOSED.

        Args:
            provider: Provider name.
        """
        self._state.pop(provider, None)

    def get_state_info(self, provider: str) -> dict:
        """
        Get detailed state information for a provider.

        Args:
            provider: Provider name.

        Returns:
            Dict with state, failures, cooldown info, or default
            CLOSED-state dict if provider has no recorded state.
        """
        info = self._state.get(provider)
        if info is None:
            return {
                "state": CircuitState.CLOSED.value,
                "consecutive_failures": 0,
                "cooldown_remaining": 0.0,
                "cooldown_multiplier": 1,
            }
        now = time.monotonic()
        remaining = max(0.0, info.get("open_until", 0) - now) if info["state"] == CircuitState.OPEN else 0.0
        return {
            "state": info["state"].value,
            "consecutive_failures": info["consecutive_failures"],
            "cooldown_remaining": remaining,
            "cooldown_multiplier": info["backoff_multiplier"],
        }

    def get_all_open_providers(self) -> list[str]:
        """
        Return providers whose circuit is currently OPEN.

        Returns:
            List of provider names in OPEN state.
        """
        result = []
        now = time.monotonic()
        for provider, info in self._state.items():
            if info["state"] == CircuitState.OPEN and now < info.get("open_until", 0):
                result.append(provider)
        return result

    # ── Internal helpers ──────────────────────────────────────────

    def _get_or_create(self, provider: str) -> dict:
        """Get or create state entry for a provider."""
        if provider not in self._state:
            self._state[provider] = {
                "state": CircuitState.CLOSED,
                "consecutive_failures": 0,
                "opened_at": 0.0,
                "open_until": 0.0,
                "test_request_allowed": False,
                "backoff_multiplier": 1,
            }
        return self._state[provider]

    def _next_cooldown(self, provider: str) -> float:
        """
        Calculate next cooldown duration with exponential backoff.

        Doubles the cooldown each time the breaker transitions to OPEN,
        starting from cooldown_base, capped at cooldown_max.

        Args:
            provider: Provider name.

        Returns:
            Cooldown duration in seconds.
        """
        info = self._get_or_create(provider)
        duration = min(
            self._cooldown_base * info["backoff_multiplier"],
            self._cooldown_max,
        )
        # Double for next time (capped at max)
        info["backoff_multiplier"] = min(
            info["backoff_multiplier"] * 2,
            int(self._cooldown_max / self._cooldown_base) + 1,
        )
        return duration
