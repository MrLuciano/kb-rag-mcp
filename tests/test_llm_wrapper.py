"""Unit tests for kb_server/evaluation/llm_wrapper.py.

Uses httpx.MockTransport to avoid live HTTP calls.
"""
import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from kb_server.evaluation.llm_wrapper import (
    BACKEND_MAP,
    BaseLLMWrapper,
    LMStudioRestWrapper,
    LMStudioSDKWrapper,
    OllamaWrapper,
    OpenAICompatWrapper,
    RAGASLLMAdapter,
    create_llm_wrapper,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _mock_transport(json_data: dict, status: int = 200):
    """Return an httpx.MockTransport that replies with JSON."""

    def handler(request: httpx.Request):
        return httpx.Response(
            status,
            json=json_data,
            headers={"content-type": "application/json"},
        )

    return httpx.MockTransport(handler)


# ── Factory tests ───────────────────────────────────────────────────────────


class TestCreateLLMWrapper:
    def test_lmstudio_rest(self):
        w = create_llm_wrapper("lmstudio-rest")
        assert isinstance(w, LMStudioRestWrapper)

    def test_lmstudio_sdk(self):
        w = create_llm_wrapper("lmstudio-sdk")
        assert isinstance(w, LMStudioSDKWrapper)

    def test_openai_compat(self):
        w = create_llm_wrapper("openai-compat")
        assert isinstance(w, OpenAICompatWrapper)

    def test_ollama(self):
        w = create_llm_wrapper("ollama")
        assert isinstance(w, OllamaWrapper)

    def test_unsupported_backend(self):
        with pytest.raises(ValueError) as exc_info:
            create_llm_wrapper("unsupported")
        assert "unsupported" in str(exc_info.value)


# ── LMStudioRestWrapper tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lmstudio_rest_invoke():
    mock_resp = {
        "choices": [
            {"message": {"content": "  Hello from LM Studio  "}}
        ]
    }
    transport = _mock_transport(mock_resp)
    async with httpx.AsyncClient(transport=transport) as client:
        with patch(
            "kb_server.evaluation.llm_wrapper._http_client", client
        ):
            wrapper = LMStudioRestWrapper(
                base_url="http://localhost:1234",
                model="test-model",
            )
            result = await wrapper.invoke("Say hello")
    assert result == "Hello from LM Studio"


# ── OpenAICompatWrapper tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_openai_compat_invoke():
    mock_resp = {
        "choices": [
            {"message": {"content": "  Hello from OpenAI  "}}
        ]
    }
    transport = _mock_transport(mock_resp)
    async with httpx.AsyncClient(transport=transport) as client:
        with patch(
            "kb_server.evaluation.llm_wrapper._http_client", client
        ):
            wrapper = OpenAICompatWrapper(
                base_url="http://localhost:1234",
                api_key="test-key",
                model="gpt-test",
            )
            result = await wrapper.invoke("Say hello")
    assert result == "Hello from OpenAI"


# ── OllamaWrapper tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ollama_invoke():
    mock_resp = {"response": "  Hello from Ollama  "}
    transport = _mock_transport(mock_resp)
    async with httpx.AsyncClient(transport=transport) as client:
        with patch(
            "kb_server.evaluation.llm_wrapper._http_client", client
        ):
            wrapper = OllamaWrapper(
                host="http://localhost:11434",
                model="llama2",
            )
            result = await wrapper.invoke("Say hello")
    assert result == "Hello from Ollama"


# ── LMStudioSDKWrapper tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lmstudio_sdk_falls_back_on_import_error():
    """SDK wrapper falls back to REST when lmstudio package missing."""
    wrapper = LMStudioSDKWrapper(model="test")

    mock_resp = {
        "choices": [
            {"message": {"content": "Fallback response"}}
        ]
    }
    transport = _mock_transport(mock_resp)
    async with httpx.AsyncClient(transport=transport) as client:
        with patch(
            "kb_server.evaluation.llm_wrapper._http_client", client
        ):
            with patch.dict("sys.modules", {"lmstudio": None}):
                result = await wrapper.invoke("Say hello")
    assert result == "Fallback response"


# ── Batch invoke tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invoke_batch_returns_same_length():
    class FakeWrapper(BaseLLMWrapper):
        def __init__(self):
            super().__init__("test")
            self.calls: list[str] = []

        async def invoke(self, prompt: str, **kwargs) -> str:
            self.calls.append(prompt)
            return f"Response: {prompt}"

    wrapper = FakeWrapper()
    results = await wrapper.invoke_batch(["p1", "p2", "p3"])
    assert len(results) == 3
    assert results == ["Response: p1", "Response: p2", "Response: p3"]


# ── RAGASLLMAdapter tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_adapter_invoke_without_langchain():
    """Adapter returns dict fallback when langchain is not installed."""
    from unittest.mock import AsyncMock

    wrapper = AsyncMock(spec=BaseLLMWrapper)
    wrapper.invoke = AsyncMock(return_value="Adapter test")
    wrapper.model_name = "test-model"

    adapter = RAGASLLMAdapter(wrapper)

    # Force ImportError by removing langchain_core from sys.modules
    # and making __import__ fail for that specific module
    real_import = __builtins__["__import__"]

    def fake_import(name, *args, **kwargs):
        if name == "langchain_core.messages":
            raise ImportError("No module named 'langchain_core'")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        result = await adapter.invoke("Hello")

    assert isinstance(result, dict)
    assert result["content"] == "Adapter test"
    assert result["type"] == "ai"


@pytest.mark.asyncio
async def test_adapter_invoke_with_langchain():
    """Adapter returns AIMessage when langchain is available."""
    from unittest.mock import AsyncMock

    wrapper = AsyncMock(spec=BaseLLMWrapper)
    wrapper.invoke = AsyncMock(return_value="AIMessage test")
    wrapper.model_name = "test-model"

    adapter = RAGASLLMAdapter(wrapper)

    # Mock langchain_core.messages.AIMessage
    mock_aimessage_cls = MagicMock()
    mock_aimessage_cls.return_value = MagicMock(content="AIMessage test")

    real_import = __builtins__["__import__"]

    def fake_import(name, *args, **kwargs):
        if name == "langchain_core.messages":
            mod = MagicMock()
            mod.AIMessage = mock_aimessage_cls
            return mod
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        result = await adapter.invoke("Hello")

    wrapper.invoke.assert_called_once_with("Hello")
    mock_aimessage_cls.assert_called_once_with(content="AIMessage test")


class TestAdapterProperties:
    def test_model_name_passes_through(self):
        wrapper = MagicMock(spec=BaseLLMWrapper)
        wrapper.model_name = "my-model"
        adapter = RAGASLLMAdapter(wrapper)
        assert adapter.model_name == "my-model"

    def test_repr(self):
        wrapper = MagicMock(spec=BaseLLMWrapper)
        wrapper.model_name = "my-model"
        wrapper.__class__.__name__ = "TestWrapper"
        adapter = RAGASLLMAdapter(wrapper)
        r = repr(adapter)
        assert "RAGASLLMAdapter" in r
        assert "TestWrapper" in r
        assert "my-model" in r
