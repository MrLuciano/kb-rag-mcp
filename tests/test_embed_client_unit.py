"""
Unit tests for kb_server/embed_client.py.

All HTTP calls are mocked so no real embedding server is needed.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

import kb_server.embed_client as ec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


DIM = 768
FAKE_VECTOR = [0.1] * DIM
OPENAI_RESPONSE = {"data": [{"embedding": FAKE_VECTOR, "index": 0}]}
OLLAMA_RESPONSE = {"embedding": FAKE_VECTOR}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_http_client():
    """Ensure no cached HTTP client leaks between tests."""
    original = ec._http_client
    yield
    ec._http_client = original


@pytest.fixture(autouse=True)
def reset_embed_cache():
    """Clear embed cache between tests."""
    original = ec._embed_cache
    yield
    ec._embed_cache = original


# ---------------------------------------------------------------------------
# openai-compat backend
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_provider_chain():
    """Reset PROVIDER_CHAIN between tests to match initial state."""
    yield
    # Restore to single-provider openai-compat default
    ec.PROVIDER_CHAIN.clear()
    ec.PROVIDER_CHAIN.append("openai-compat")
    ec.PRIMARY_BACKEND = "openai-compat"


@pytest.mark.asyncio
async def test_openai_compat_returns_embedding(monkeypatch):
    """openai-compat: POST /v1/embeddings → returns 768 floats."""
    monkeypatch.setenv("EMBED_BACKEND", "openai-compat")
    ec.BACKEND = "openai-compat"
    ec.PROVIDER_CHAIN[:] = ["openai-compat"]
    ec.PRIMARY_BACKEND = "openai-compat"

    mock_client = AsyncMock()
    mock_client.post.return_value = _fake_response(OPENAI_RESPONSE)
    ec._http_client = mock_client

    result = await ec.get_embedding("test text", use_cache=False)

    assert isinstance(result, list)
    assert len(result) == DIM
    assert result[0] == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# ollama backend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ollama_returns_embedding(monkeypatch):
    """ollama: POST /api/embeddings → returns 768 floats."""
    monkeypatch.setenv("EMBED_BACKEND", "ollama")
    ec.BACKEND = "ollama"
    ec.PROVIDER_CHAIN[:] = ["ollama"]
    ec.PRIMARY_BACKEND = "ollama"

    mock_client = AsyncMock()
    mock_client.post.return_value = _fake_response(OLLAMA_RESPONSE)
    ec._http_client = mock_client

    result = await ec.get_embedding("test text", use_cache=False)

    assert isinstance(result, list)
    assert len(result) == DIM


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_provider_error_raises_runtime_error(monkeypatch):
    """Single provider failure → RuntimeError with all-providers-failed."""
    monkeypatch.setenv("EMBED_BACKEND", "openai-compat")
    ec.BACKEND = "openai-compat"
    ec.PROVIDER_CHAIN[:] = ["openai-compat"]
    ec.PRIMARY_BACKEND = "openai-compat"

    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("refused")
    ec._http_client = mock_client

    with pytest.raises(RuntimeError, match="All providers failed"):
        await ec.get_embedding("test", use_cache=False)


@pytest.mark.asyncio
async def test_error_clears_circuit_breaker_state(monkeypatch):
    """Provider failure increments circuit breaker consecutive failures."""
    monkeypatch.setenv("EMBED_BACKEND", "openai-compat")
    ec.BACKEND = "openai-compat"
    ec.PROVIDER_CHAIN[:] = ["openai-compat"]
    ec.PRIMARY_BACKEND = "openai-compat"

    # Reset breaker state
    ec._circuit_breaker.reset("openai-compat")

    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("refused")
    ec._http_client = mock_client

    with pytest.raises(RuntimeError):
        await ec.get_embedding("test", use_cache=False)

    # Failure should be recorded
    assert ec._circuit_breaker.get_failure_count("openai-compat") >= 1


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_embeddings_batch_returns_same_length(monkeypatch):
    """get_embeddings_batch returns list with same length as input."""
    monkeypatch.setenv("EMBED_BACKEND", "openai-compat")
    ec.BACKEND = "openai-compat"
    ec.PROVIDER_CHAIN[:] = ["openai-compat"]
    ec.PRIMARY_BACKEND = "openai-compat"

    texts = ["text one", "text two", "text three"]
    batch_response = {
        "data": [
            {"embedding": FAKE_VECTOR, "index": 0},
            {"embedding": FAKE_VECTOR, "index": 1},
            {"embedding": FAKE_VECTOR, "index": 2},
        ]
    }
    mock_client = AsyncMock()
    mock_client.post.return_value = _fake_response(batch_response)
    ec._http_client = mock_client
    ec._embed_cache = None

    result = await ec.get_embeddings_batch(texts, use_cache=False)

    assert len(result) == len(texts)
    assert all(len(v) == DIM for v in result)


# ---------------------------------------------------------------------------
# Cache behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_use_cache_false_bypasses_cache(monkeypatch):
    """use_cache=False skips cache lookup and storage."""
    monkeypatch.setenv("EMBED_BACKEND", "openai-compat")
    ec.BACKEND = "openai-compat"
    ec.PROVIDER_CHAIN[:] = ["openai-compat"]
    ec.PRIMARY_BACKEND = "openai-compat"

    mock_cache = MagicMock()
    ec._embed_cache = mock_cache

    mock_client = AsyncMock()
    mock_client.post.return_value = _fake_response(OPENAI_RESPONSE)
    ec._http_client = mock_client

    await ec.get_embedding("hello", use_cache=False)

    mock_cache.get.assert_not_called()
    mock_cache.put.assert_not_called()


@pytest.mark.asyncio
async def test_use_cache_true_caches_result(monkeypatch):
    """use_cache=True caches result; second identical call returns cached value."""
    monkeypatch.setenv("EMBED_BACKEND", "openai-compat")
    ec.BACKEND = "openai-compat"
    ec.PROVIDER_CHAIN[:] = ["openai-compat"]
    ec.PRIMARY_BACKEND = "openai-compat"

    # Set up cache with a miss then a hit
    mock_cache = MagicMock()
    mock_cache.get.side_effect = [None, FAKE_VECTOR]  # miss, then hit
    mock_cache.hash_key.return_value = "some-key"
    ec._embed_cache = mock_cache

    mock_client = AsyncMock()
    mock_client.post.return_value = _fake_response(OPENAI_RESPONSE)
    ec._http_client = mock_client

    result1 = await ec.get_embedding("hello", use_cache=True)
    result2 = await ec.get_embedding("hello", use_cache=True)

    # First call: miss → HTTP request; second call: hit → no extra HTTP
    mock_cache.put.assert_called_once()
    assert result2 == FAKE_VECTOR


# ---------------------------------------------------------------------------
# get_embed_dim
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Provider resilience
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_circuit_breaker_blocks_open_provider(monkeypatch):
    """Circuit breaker OPEN state blocks dispatch to that provider."""
    monkeypatch.setenv("EMBED_BACKEND", "provider_a;provider_b")
    ec.BACKEND = "provider_a;provider_b"
    ec.PROVIDER_CHAIN[:] = ["provider_a", "provider_b"]
    ec.PRIMARY_BACKEND = "provider_a"

    # Set circuit breaker to OPEN for provider_a
    ec._circuit_breaker.record_failure("provider_a")
    ec._circuit_breaker.record_failure("provider_a")
    ec._circuit_breaker.record_failure("provider_a")
    ec._circuit_breaker.record_failure("provider_a")
    ec._circuit_breaker.record_failure("provider_a")

    # Mock provider_b (the fallback) to work
    monkeypatch.setitem(ec._BACKENDS, "provider_a", AsyncMock())
    mock_provider_b = AsyncMock(return_value=FAKE_VECTOR)
    monkeypatch.setitem(ec._BACKENDS, "provider_b", mock_provider_b)

    result = await ec.get_embedding("test", use_cache=False)

    assert result == FAKE_VECTOR
    mock_provider_b.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_on_provider_failure(monkeypatch):
    """When primary fails, falls back to next provider in chain."""
    monkeypatch.setenv("EMBED_BACKEND", "provider_c;provider_d")
    ec.BACKEND = "provider_c;provider_d"
    ec.PROVIDER_CHAIN[:] = ["provider_c", "provider_d"]
    ec.PRIMARY_BACKEND = "provider_c"

    # Reset circuit breaker for test providers
    ec._circuit_breaker.reset("provider_c")
    ec._circuit_breaker.reset("provider_d")

    # Mock provider_c to fail, provider_d to succeed
    mock_provider_c = AsyncMock(side_effect=httpx.ConnectError("refused"))
    mock_provider_d = AsyncMock(return_value=FAKE_VECTOR)
    monkeypatch.setitem(ec._BACKENDS, "provider_c", mock_provider_c)
    monkeypatch.setitem(ec._BACKENDS, "provider_d", mock_provider_d)

    result = await ec.get_embedding("test", use_cache=False)

    assert result == FAKE_VECTOR
    mock_provider_c.assert_called_once()
    mock_provider_d.assert_called_once()
    assert ec._circuit_breaker.get_failure_count("provider_c") >= 1


@pytest.mark.asyncio
async def test_budget_exhaustion_triggers_fallback(monkeypatch):
    """When primary budget is exhausted, falls back to next provider."""
    monkeypatch.setenv("EMBED_BACKEND", "provider_e;provider_f")
    ec.BACKEND = "provider_e;provider_f"
    ec.PROVIDER_CHAIN[:] = ["provider_e", "provider_f"]
    ec.PRIMARY_BACKEND = "provider_e"

    # Exhaust provider_e budget (max_requests=100)
    for _ in range(100):
        ec._provider_budget.record_request("provider_e")

    # Mock providers
    mock_provider_e = AsyncMock(return_value=FAKE_VECTOR)
    mock_provider_f = AsyncMock(return_value=FAKE_VECTOR)
    monkeypatch.setitem(ec._BACKENDS, "provider_e", mock_provider_e)
    monkeypatch.setitem(ec._BACKENDS, "provider_f", mock_provider_f)

    result = await ec.get_embedding("test", use_cache=False)

    assert result == FAKE_VECTOR
    mock_provider_e.assert_not_called()  # Skipped by budget check
    mock_provider_f.assert_called_once()


@pytest.mark.asyncio
async def test_all_providers_fail_raises_runtime_error(monkeypatch):
    """When all providers fail, RuntimeError is raised."""
    monkeypatch.setenv("EMBED_BACKEND", "provider_g;provider_h")
    ec.BACKEND = "provider_g;provider_h"
    ec.PROVIDER_CHAIN[:] = ["provider_g", "provider_h"]
    ec.PRIMARY_BACKEND = "provider_g"

    ec._circuit_breaker.reset("provider_g")
    ec._circuit_breaker.reset("provider_h")

    # Both providers fail
    mock_provider_g = AsyncMock(side_effect=httpx.ConnectError("refused"))
    mock_provider_h = AsyncMock(side_effect=httpx.ConnectError("refused"))
    monkeypatch.setitem(ec._BACKENDS, "provider_g", mock_provider_g)
    monkeypatch.setitem(ec._BACKENDS, "provider_h", mock_provider_h)

    with pytest.raises(RuntimeError, match="All providers failed"):
        await ec.get_embedding("test", use_cache=False)


@pytest.mark.asyncio
async def test_success_resets_circuit_breaker(monkeypatch):
    """Successful request resets circuit breaker failure count."""
    monkeypatch.setenv("EMBED_BACKEND", "openai-compat")
    ec.BACKEND = "openai-compat"
    ec.PROVIDER_CHAIN[:] = ["openai-compat"]
    ec.PRIMARY_BACKEND = "openai-compat"

    ec._circuit_breaker.reset("openai-compat")
    ec._circuit_breaker.record_failure("openai-compat")
    ec._circuit_breaker.record_failure("openai-compat")
    assert ec._circuit_breaker.get_failure_count("openai-compat") == 2

    mock_client = AsyncMock()
    mock_client.post.return_value = _fake_response(OPENAI_RESPONSE)
    ec._http_client = mock_client

    await ec.get_embedding("test", use_cache=False)

    # Success should reset failure count
    assert ec._circuit_breaker.get_failure_count("openai-compat") == 0


# ---------------------------------------------------------------------------
# validate_providers
# ---------------------------------------------------------------------------


def test_validate_providers_known_provider():
    """validate_providers does not raise for known provider."""
    ec.PROVIDER_CHAIN[:] = ["openai-compat"]
    ec.validate_providers()  # Should not raise


def test_validate_providers_unknown_provider():
    """validate_providers raises ValueError for unknown provider."""
    ec.PROVIDER_CHAIN[:] = ["nonexistent-provider"]
    with pytest.raises(ValueError, match="Invalid provider"):
        ec.validate_providers()


# ---------------------------------------------------------------------------
# get_embed_dim
# ---------------------------------------------------------------------------


def test_get_embed_dim_returns_positive_integer(monkeypatch):
    """get_embed_dim() always returns a positive integer."""
    dim = ec.get_embed_dim()
    assert isinstance(dim, int)
    assert dim > 0
