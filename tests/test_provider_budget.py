"""
Tests for kb_server/provider_budget.py.

PHASE 36: Provider Budget & Circuit Breaker
"""

import time

import pytest

from kb_server.provider_budget import ProviderBudget


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def budget():
    """Provider budget with small window and low limits for easy testing."""
    return ProviderBudget(
        window_seconds=0.05,  # 50ms window for fast tests
        max_requests=3,
        max_tokens=100,
    )


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_budget_allows_request_initially(budget):
    """A new provider always has budget available."""
    assert budget.check_budget("openai-compat") is True


def test_budget_remaining_full_initially(budget):
    """budget_remaining returns 1.0 for a provider with no usage."""
    ratio = budget.budget_remaining("openai-compat")
    assert ratio == pytest.approx(1.0)
    assert 0.0 <= ratio <= 1.0


# ---------------------------------------------------------------------------
# Request tracking
# ---------------------------------------------------------------------------


def test_record_request_increases_count(budget):
    """record_request increments tracked usage."""
    budget.record_request("provider_a")
    usage = budget.get_usage("provider_a")
    assert usage["request_count"] == 1
    assert usage["remaining"] == 2


def test_multiple_requests_tracked(budget):
    """Multiple requests are correctly tracked."""
    budget.record_request("provider_b")
    budget.record_request("provider_b")

    usage = budget.get_usage("provider_b")
    assert usage["request_count"] == 2
    assert usage["remaining"] == 1


# ---------------------------------------------------------------------------
# Budget exhaustion
# ---------------------------------------------------------------------------


def test_budget_exhausted_at_limit(budget):
    """check_budget returns False when request limit reached."""
    budget.record_request("provider_c")
    budget.record_request("provider_c")
    budget.record_request("provider_c")

    assert budget.check_budget("provider_c") is False


def test_budget_allows_at_limit_minus_one(budget):
    """check_budget returns True when just under the limit."""
    budget.record_request("provider_d")
    budget.record_request("provider_d")

    assert budget.check_budget("provider_d") is True


# ---------------------------------------------------------------------------
# Sliding window expiry
# ---------------------------------------------------------------------------


def test_budget_recovers_after_window_expiry(budget):
    """After window expires, budget becomes available again."""
    budget.record_request("provider_e")
    budget.record_request("provider_e")
    budget.record_request("provider_e")

    assert budget.check_budget("provider_e") is False

    # Wait for window to expire
    time.sleep(0.06)

    assert budget.check_budget("provider_e") is True


def test_get_usage_updates_after_window_expiry(budget):
    """get_usage reflects purged entries after window expiry."""
    budget.record_request("provider_f")
    budget.record_request("provider_f")
    budget.record_request("provider_f")

    time.sleep(0.06)
    usage = budget.get_usage("provider_f")

    assert usage["request_count"] == 0
    assert usage["remaining"] == 3


# ---------------------------------------------------------------------------
# Token tracking
# ---------------------------------------------------------------------------


def test_token_tracking(budget):
    """record_request with tokens tracks token usage."""
    budget.record_request("provider_g", tokens=30)
    usage = budget.get_usage("provider_g")
    assert usage["token_count"] == 30
    assert usage["token_limit"] == 100
    assert usage["tokens_remaining"] == 70


def test_token_budget_exhaustion(budget):
    """check_budget returns False when token limit reached."""
    budget.record_request("provider_h", tokens=60)
    budget.record_request("provider_h", tokens=50)
    # Total: 110 tokens, over 100 limit
    assert budget.check_budget("provider_h") is False


def test_token_and_request_budget_mixed(budget):
    """Both request count and token count are considered."""
    budget.record_request("provider_i", tokens=30)

    usage = budget.get_usage("provider_i")
    assert usage["token_count"] == 30
    assert usage["request_count"] == 1


# ---------------------------------------------------------------------------
# budget_remaining ratio
# ---------------------------------------------------------------------------


def test_budget_remaining_decreases(budget):
    """budget_remaining decreases as requests are made."""
    r0 = budget.budget_remaining("provider_j")
    assert r0 == pytest.approx(1.0)

    budget.record_request("provider_j")
    r1 = budget.budget_remaining("provider_j")
    assert r1 < r0

    budget.record_request("provider_j")
    r2 = budget.budget_remaining("provider_j")
    assert r2 < r1


def test_budget_remaining_exhausted(budget):
    """budget_remaining is 0.0 at request limit."""
    budget.record_request("provider_k")
    budget.record_request("provider_k")
    budget.record_request("provider_k")

    assert budget.budget_remaining("provider_k") == pytest.approx(0.0)


def test_budget_remaining_recovers(budget):
    """budget_remaining recovers after window expiry."""
    budget.record_request("provider_l")
    budget.record_request("provider_l")
    budget.record_request("provider_l")

    assert budget.budget_remaining("provider_l") == pytest.approx(0.0)

    time.sleep(0.06)

    assert budget.budget_remaining("provider_l") == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def test_reset_provider_clears_usage(budget):
    """reset_provider clears all usage for a specific provider."""
    budget.record_request("provider_m")
    budget.record_request("provider_m")
    assert budget.get_usage("provider_m")["request_count"] == 2

    budget.reset_provider("provider_m")
    assert budget.get_usage("provider_m")["request_count"] == 0


def test_reset_provider_does_not_affect_others(budget):
    """reset_provider only affects the specified provider."""
    budget.record_request("provider_n")
    budget.record_request("provider_o")
    budget.record_request("provider_o")

    budget.reset_provider("provider_n")

    assert budget.get_usage("provider_n")["request_count"] == 0
    assert budget.get_usage("provider_o")["request_count"] == 2


def test_reset_all_clears_everything(budget):
    """reset_all clears usage for all providers."""
    budget.record_request("provider_p")
    budget.record_request("provider_q")

    budget.reset_all()

    assert budget.get_usage("provider_p")["request_count"] == 0
    assert budget.get_usage("provider_q")["request_count"] == 0


# ---------------------------------------------------------------------------
# Per-provider isolation
# ---------------------------------------------------------------------------


def test_providers_have_independent_budgets(budget):
    """Budget for one provider does not affect another."""
    budget.record_request("provider_r")
    budget.record_request("provider_r")
    budget.record_request("provider_r")

    # provider_r exhausted
    assert budget.check_budget("provider_r") is False
    # provider_s still has budget
    assert budget.check_budget("provider_s") is True


# ---------------------------------------------------------------------------
# Default config
# ---------------------------------------------------------------------------


def test_default_config():
    """Default budget config matches expected production values."""
    b = ProviderBudget()
    assert b._window_seconds == 60.0
    assert b._max_requests == 100
    assert b._max_tokens is None
