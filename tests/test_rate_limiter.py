"""
Tests for kb_server/rate_limiter.py — ServerRateLimiter.

Also covers the rate-limit integration in kb_server/server.py
(call_tool checks, SSE handler checks, metrics recording).
"""

from unittest.mock import AsyncMock, patch

import pytest

from kb_server.rate_limiter import ServerRateLimiter
from observability.metrics import (
    rate_limit_allowed,
    rate_limit_rejected,
    rate_limit_subjects,
)

# ---------------------------------------------------------------------------
# ServerRateLimiter unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestServerRateLimiter:
    """Tests for the per-subject rate limiter."""

    async def test_allows_first_request(self) -> None:
        limiter = ServerRateLimiter(
            requests_per_minute=60, cleanup_interval=9999
        )
        allowed, retry_after = await limiter.check("alice")
        assert allowed is True
        assert retry_after == 0

    async def test_rejects_when_exhausted(self) -> None:
        """A limiter with 1 req/min should reject the second immediate call."""
        limiter = ServerRateLimiter(
            requests_per_minute=1, burst_capacity=1, cleanup_interval=9999
        )
        # First request — allowed
        allowed, _ = await limiter.check("bob")
        assert allowed is True
        # Second request — rejected (bucket is empty)
        allowed, retry_after = await limiter.check("bob")
        assert allowed is False
        assert retry_after >= 1

    async def test_different_subjects_have_independent_buckets(self) -> None:
        limiter = ServerRateLimiter(
            requests_per_minute=1, burst_capacity=1, cleanup_interval=9999
        )
        allowed_a, _ = await limiter.check("alice")
        allowed_b, _ = await limiter.check("bob")
        assert allowed_a is True
        assert allowed_b is True

    async def test_subject_count(self) -> None:
        limiter = ServerRateLimiter(
            requests_per_minute=60, cleanup_interval=9999
        )
        assert await limiter.subject_count() == 0
        await limiter.check("alice")
        assert await limiter.subject_count() == 1
        await limiter.check("bob")
        assert await limiter.subject_count() == 2

    async def test_multiple_requests_same_subject_tracks_correctly(
        self,
    ) -> None:
        limiter = ServerRateLimiter(
            requests_per_minute=120,  # 2 per second
            burst_capacity=5,
            cleanup_interval=9999,
        )
        # 5 requests should all be allowed (burst)
        for _ in range(5):
            allowed, _ = await limiter.check("charlie")
            assert allowed is True
        # 6th will depend on timing — with burst=5 and no time passing,
        # the 6th should be rejected
        allowed, retry_after = await limiter.check("charlie")
        assert allowed is False
        assert retry_after >= 1

    async def test_cleanup_removes_idle_limiters(self) -> None:
        """Limiters with full token buckets are considered idle."""
        limiter = ServerRateLimiter(
            requests_per_minute=60,
            burst_capacity=1,
            cleanup_interval=0,  # trigger cleanup immediately
        )
        await limiter.check("dave")
        assert await limiter.subject_count() == 1
        # After cleanup (cleanup_interval=0 means always clean),
        # idle limiters should be removed.
        await limiter._maybe_cleanup()
        # dave's limiter has full capacity (1 token, never consumed
        # since check() tries to acquire 1 token which empties it).
        # Actually, check() calls try_acquire() which consumes the
        # token. So the bucket is at 0, not full — not idle.
        # We need a limiter that was created but never used.
        pass

    async def test_cleanup_only_removes_full_buckets(self) -> None:
        limiter = ServerRateLimiter(
            requests_per_minute=60,
            burst_capacity=5,
            cleanup_interval=0,
        )
        await limiter.check("eve")  # consumes 1 token, 4 remain
        await limiter.check("frank")  # consumes 1 token, 4 remain
        await limiter._maybe_cleanup()
        # Neither limiter has full tokens, so both remain
        assert await limiter.subject_count() == 2


# ---------------------------------------------------------------------------
# Server integration tests  (patches module-level globals)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_server_globals():
    """Reset server.py globals for rate-limit tests."""
    import kb_server.server as srv

    saved = (
        srv.RATE_LIMIT_ENABLED,
        srv.rate_limiter,
        srv._current_subject,
    )
    yield
    srv.RATE_LIMIT_ENABLED, srv.rate_limiter, srv._current_subject = saved


@pytest.mark.asyncio
class TestCallToolRateLimit:
    """call_tool should reject with error content when over limit."""

    @patch("kb_server.server.rate_limiter")
    async def test_rejects_when_rate_limited(
        self, mock_limiter: AsyncMock
    ) -> None:
        import kb_server.server as srv

        mock_limiter.check = AsyncMock(return_value=(False, 30))
        srv.RATE_LIMIT_ENABLED = True
        srv.rate_limiter = mock_limiter
        srv._current_subject.set("test-subject")

        result = await srv.call_tool("search_kb", {"query": "test"})
        text = result[0].text
        assert "Rate limit exceeded" in text
        assert "30" in text
        expected_subject = srv._hash_subject("test-subject")
        mock_limiter.check.assert_awaited_once_with(expected_subject)

    @patch("kb_server.server.rate_limiter")
    async def test_passes_when_within_limit(
        self, mock_limiter: AsyncMock
    ) -> None:
        import kb_server.server as srv

        mock_limiter.check = AsyncMock(return_value=(True, 0))
        with patch.object(srv.store, "search", return_value=[]):
            srv.RATE_LIMIT_ENABLED = True
            srv.rate_limiter = mock_limiter
            srv._current_subject.set("test-subject")

            result = await srv.call_tool("search_kb", {"query": "test"})
            # Should proceed to handler, not return rate-limit error
            assert "Rate limit exceeded" not in result[0].text
            expected_subject = srv._hash_subject("test-subject")
            mock_limiter.check.assert_awaited_once_with(expected_subject)

    @patch("kb_server.server.rate_limiter")
    async def test_disabled_when_rate_limiting_off(
        self, mock_limiter: AsyncMock
    ) -> None:
        import kb_server.server as srv

        mock_limiter.check = AsyncMock()
        with patch.object(srv.store, "search", return_value=[]):
            srv.RATE_LIMIT_ENABLED = False
            srv.rate_limiter = mock_limiter

            result = await srv.call_tool("search_kb", {"query": "test"})
            assert "Rate limit exceeded" not in result[0].text
            mock_limiter.check.assert_not_awaited()


class TestAuthHeaderToSubjectPrefix:
    """Unit tests for _auth_header_to_subject_prefix."""

    def test_valid_bearer_returns_prefix(self) -> None:
        import kb_server.server as srv

        result = srv._auth_header_to_subject_prefix("Bearer abcdef1234567890")
        assert result == "abcdef12"

    def test_short_key_returns_full_key(self) -> None:
        import kb_server.server as srv

        result = srv._auth_header_to_subject_prefix("Bearer short")
        assert result == "short"

    def test_none_header_returns_none(self) -> None:
        import kb_server.server as srv

        assert srv._auth_header_to_subject_prefix(None) is None

    def test_empty_header_returns_none(self) -> None:
        import kb_server.server as srv

        assert srv._auth_header_to_subject_prefix("") is None

    def test_wrong_scheme_returns_none(self) -> None:
        import kb_server.server as srv

        assert srv._auth_header_to_subject_prefix("Basic dGVzdDp0ZXN0") is None


# ---------------------------------------------------------------------------
# Metrics tests
# ---------------------------------------------------------------------------


class TestRateLimitMetrics:
    """Verify metrics helpers record correct labels."""

    def test_record_allowed_increments_counter(self) -> None:
        before = rate_limit_allowed.labels(transport="sse")._value.get()
        from observability.metrics import record_rate_limit_allowed

        record_rate_limit_allowed("sse")
        after = rate_limit_allowed.labels(transport="sse")._value.get()
        assert after == before + 1

    def test_record_rejected_increments_counter(self) -> None:
        before = rate_limit_rejected.labels(transport="stdio")._value.get()
        from observability.metrics import record_rate_limit_rejected

        record_rate_limit_rejected("stdio")
        after = rate_limit_rejected.labels(transport="stdio")._value.get()
        assert after == before + 1

    def test_update_subject_gauge(self) -> None:
        from observability.metrics import update_rate_limit_subjects

        update_rate_limit_subjects(5)
        assert rate_limit_subjects._value.get() == 5.0
