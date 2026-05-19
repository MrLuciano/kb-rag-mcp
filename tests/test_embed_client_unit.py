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


@pytest.mark.asyncio
async def test_openai_compat_returns_embedding(monkeypatch):
    """openai-compat: POST /v1/embeddings → returns 768 floats."""
    monkeypatch.setenv("EMBED_BACKEND", "openai-compat")
    # Reset module-level BACKEND var
    ec.BACKEND = "openai-compat"

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
async def test_http_500_raises(monkeypatch):
    """HTTP 500 → HTTPStatusError is raised (not silenced)."""
    monkeypatch.setenv("EMBED_BACKEND", "openai-compat")
    ec.BACKEND = "openai-compat"

    mock_client = AsyncMock()
    mock_client.post.return_value = _fake_response({}, status_code=500)
    ec._http_client = mock_client

    with pytest.raises(httpx.HTTPStatusError):
        await ec.get_embedding("test", use_cache=False)


@pytest.mark.asyncio
async def test_connect_error_propagates(monkeypatch):
    """ConnectError → exception propagates (not silently swallowed)."""
    monkeypatch.setenv("EMBED_BACKEND", "openai-compat")
    ec.BACKEND = "openai-compat"

    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("refused")
    ec._http_client = mock_client

    with pytest.raises(httpx.ConnectError):
        await ec.get_embedding("test", use_cache=False)


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_embeddings_batch_returns_same_length(monkeypatch):
    """get_embeddings_batch returns list with same length as input."""
    monkeypatch.setenv("EMBED_BACKEND", "openai-compat")
    ec.BACKEND = "openai-compat"

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


def test_get_embed_dim_returns_positive_integer(monkeypatch):
    """get_embed_dim() always returns a positive integer."""
    dim = ec.get_embed_dim()
    assert isinstance(dim, int)
    assert dim > 0
