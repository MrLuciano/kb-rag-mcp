"""
Tests for kb_server/circuit_breaker.py.

PHASE 36: Provider Budget & Circuit Breaker
"""

import time

import pytest

from kb_server.circuit_breaker import CircuitBreaker, CircuitState

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cb():
    """Circuit breaker with low thresholds for easy testing."""
    return CircuitBreaker(
        failure_threshold=3,
        cooldown_base=0.01,  # Fast cooldown for testing
        cooldown_max=0.1,
    )


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_initial_state_is_closed(cb):
    """A brand-new circuit breaker starts CLOSED for any provider."""
    state = cb.check("openai-compat")
    assert state == CircuitState.CLOSED


def test_initial_failure_count_is_zero(cb):
    """Failure count starts at zero for a new provider."""
    assert cb.get_failure_count("openai-compat") == 0


def test_is_open_false_initially(cb):
    """is_open() returns False for a provider that has never failed."""
    assert cb.is_open("openai-compat") is False


# ---------------------------------------------------------------------------
# State transitions: CLOSED -> OPEN
# ---------------------------------------------------------------------------


def test_threshold_failures_opens_circuit(cb):
    """Consecutive failures equal to threshold transition to OPEN."""
    # CLOSED with 1 failure (below 3)
    assert cb.record_failure("provider_a") == CircuitState.CLOSED
    assert cb.record_failure("provider_a") == CircuitState.CLOSED

    # 3rd failure triggers OPEN
    new_state = cb.record_failure("provider_a")
    assert new_state == CircuitState.OPEN
    assert cb.is_open("provider_a") is True
    assert cb.check("provider_a") == CircuitState.OPEN


def test_below_threshold_stays_closed(cb):
    """Failure count below threshold keeps circuit CLOSED."""
    cb.record_failure("provider_b")
    cb.record_failure("provider_b")

    assert cb.get_failure_count("provider_b") == 2
    assert cb.is_open("provider_b") is False


# ---------------------------------------------------------------------------
# State transitions: OPEN -> HALF_OPEN
# ---------------------------------------------------------------------------


def test_open_transitions_to_half_open_after_cooldown(cb):
    """After cooldown, OPEN transitions to HALF_OPEN automatically."""
    cb.record_failure("provider_c")
    cb.record_failure("provider_c")
    cb.record_failure("provider_c")

    assert cb.check("provider_c") == CircuitState.OPEN

    # Wait for cooldown
    time.sleep(0.015)

    state = cb.check("provider_c")
    assert state == CircuitState.HALF_OPEN


def test_half_open_test_request_allowed_flag(cb):
    """HALF_OPEN sets test_request_allowed flag."""
    cb.record_failure("provider_d")
    cb.record_failure("provider_d")
    cb.record_failure("provider_d")

    time.sleep(0.015)
    cb.check("provider_d")

    # The flag is set internally
    info = cb._state["provider_d"]
    assert info["test_request_allowed"] is True


# ---------------------------------------------------------------------------
# State transitions: HALF_OPEN -> CLOSED (success heals)
# ---------------------------------------------------------------------------


def test_half_open_success_transitions_to_closed(cb):
    """A successful request in HALF_OPEN transitions to CLOSED."""
    cb.record_failure("provider_e")
    cb.record_failure("provider_e")
    cb.record_failure("provider_e")

    time.sleep(0.015)
    cb.check("provider_e")
    assert cb.check("provider_e") == CircuitState.HALF_OPEN

    cb.record_success("provider_e")
    assert cb.check("provider_e") == CircuitState.CLOSED
    assert cb.is_open("provider_e") is False


def test_half_open_success_resets_failure_count(cb):
    """Successful HALF_OPEN test resets failure count to zero."""
    cb.record_failure("provider_f")
    cb.record_failure("provider_f")
    cb.record_failure("provider_f")

    time.sleep(0.015)
    cb.check("provider_f")
    cb.record_success("provider_f")

    assert cb.get_failure_count("provider_f") == 0


# ---------------------------------------------------------------------------
# State transitions: HALF_OPEN -> OPEN (test fails)
# ---------------------------------------------------------------------------


def test_half_open_failure_returns_to_open(cb):
    """A failed request in HALF_OPEN transitions back to OPEN."""
    cb.record_failure("provider_g")
    cb.record_failure("provider_g")
    cb.record_failure("provider_g")

    time.sleep(0.015)
    cb.check("provider_g")

    # Test request fails
    assert cb.record_failure("provider_g") == CircuitState.OPEN


def test_half_open_failure_increases_cooldown_exponential(cb):
    """HALF_OPEN failure uses increased cooldown (exponential backoff)."""
    breaker = CircuitBreaker(
        failure_threshold=2,
        cooldown_base=0.02,
        cooldown_max=0.5,
    )

    # First OPEN cycle
    breaker.record_failure("provider_h")
    breaker.record_failure("provider_h")
    assert breaker.check("provider_h") == CircuitState.OPEN

    # Wait and heal
    time.sleep(0.025)
    breaker.check("provider_h")
    breaker.record_success("provider_h")

    # Second OPEN cycle (fail again)
    breaker.record_failure("provider_h")
    breaker.record_failure("provider_h")
    info = breaker._state["provider_h"]

    # Cooldown should be doubled (0.02 * 2 = 0.04)
    cooldown = info["open_until"] - info["opened_at"]
    assert cooldown >= 0.03, f"Expected increased cooldown, got {cooldown}"
    assert cooldown <= 0.06, f"Cooldown too high: {cooldown}"


# ---------------------------------------------------------------------------
# Success in CLOSED state
# ---------------------------------------------------------------------------


def test_success_resets_failure_count(cb):
    """A successful request in CLOSED resets consecutive failure count."""
    cb.record_failure("provider_i")
    cb.record_failure("provider_i")
    assert cb.get_failure_count("provider_i") == 2

    cb.record_success("provider_i")

    assert cb.get_failure_count("provider_i") == 0
    assert cb.is_open("provider_i") is False


# ---------------------------------------------------------------------------
# get_state_info
# ---------------------------------------------------------------------------


def test_get_state_info_closed(cb):
    """get_state_info returns CLOSED state info."""
    info = cb.get_state_info("provider_j")
    assert info["state"] == "closed"
    assert info["consecutive_failures"] == 0


def test_get_state_info_open(cb):
    """get_state_info returns OPEN state with cooldown info."""
    cb.record_failure("provider_k")
    cb.record_failure("provider_k")
    cb.record_failure("provider_k")

    info = cb.get_state_info("provider_k")
    assert info["state"] == "open"
    assert info["consecutive_failures"] == 3
    assert info["cooldown_remaining"] > 0


def test_get_state_info_unknown_provider(cb):
    """get_state_info returns default CLOSED state for unknown provider."""
    info = cb.get_state_info("nonexistent")
    assert info["state"] == "closed"
    assert info["consecutive_failures"] == 0
    assert info["cooldown_remaining"] == 0.0


# ---------------------------------------------------------------------------
# get_all_open_providers
# ---------------------------------------------------------------------------


def test_get_all_open_providers_empty(cb):
    """get_all_open_providers returns empty list when nothing is open."""
    assert cb.get_all_open_providers() == []


def test_get_all_open_providers_returns_open(cb):
    """get_all_open_providers returns providers in OPEN state."""
    cb.record_failure("provider_l")
    cb.record_failure("provider_l")
    cb.record_failure("provider_l")

    open_providers = cb.get_all_open_providers()
    assert "provider_l" in open_providers
    assert len(open_providers) == 1


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def test_reset_clears_provider_state(cb):
    """reset() removes all state for a provider."""
    cb.record_failure("provider_m")
    cb.record_failure("provider_m")
    cb.record_failure("provider_m")

    assert cb.is_open("provider_m") is True

    cb.reset("provider_m")

    assert cb.is_open("provider_m") is False
    assert cb.check("provider_m") == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# Per-provider isolation
# ---------------------------------------------------------------------------


def test_providers_are_independent(cb):
    """Failures in one provider do not affect another."""
    cb.record_failure("provider_n")
    cb.record_failure("provider_n")
    cb.record_failure("provider_n")

    assert cb.is_open("provider_n") is True
    assert cb.is_open("provider_o") is False
    assert cb.check("provider_o") == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# Cooldown values
# ---------------------------------------------------------------------------


def test_default_cooldown_values():
    """Default cooldown config matches expected production values."""
    breaker = CircuitBreaker()
    assert breaker._cooldown_base == 30.0
    assert breaker._cooldown_max == 300.0
    assert breaker._failure_threshold == 5
