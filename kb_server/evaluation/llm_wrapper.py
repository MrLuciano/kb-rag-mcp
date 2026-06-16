"""
Langchain-compatible LLM wrapper for RAGAS evaluation.

Adapts kb-rag-mcp's existing HTTP-based text-generation backends
(LM Studio REST, Ollama, OpenAI-compat) to the interface expected by
RAGAS's ``evaluate(llm=...)`` parameter.

Text-generation endpoints per backend
─────────────────────────────────────
lmstudio-rest  →  POST {LMS_BASE_URL}/v1/chat/completions
                  Request body: {model, messages}
                  Response: {choices[0].message.content}

openai-compat  →  Same as lmstudio-rest (OpenAI-compat format)

ollama         →  POST {OLLAMA_HOST}/api/generate
                  Body: {"model": "...", "prompt": "...", "stream": false}
                  Response: {"response": "..."}

lmstudio-sdk   →  lms.ChatCompletion.create(...)  (if SDK installed)
                  Falls back to lmstudio-rest if SDK unavailable.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, List, Optional, cast

import httpx

log = logging.getLogger("kb-mcp.eval")

# ── Config mirroring embed_client ────────────────────────────────────────

LMS_BASE_URL = os.getenv("LMS_BASE_URL", "http://localhost:1234")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

DEFAULT_LLM_MODEL = os.getenv(
    "EVAL_LLM_MODEL",
    os.getenv("LLM_MODEL", "default"),
)

# ── HTTP client (shared) ───────────────────────────────────────────────

_http_client: httpx.AsyncClient | None = None


async def _http() -> httpx.AsyncClient:
    """Lazy async HTTP client."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=60.0)
    return _http_client


# ── Abstract base ────────────────────────────────────────────────────────


class BaseLLMWrapper(ABC):
    """Abstract wrapper for text-generation backends."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or DEFAULT_LLM_MODEL

    @abstractmethod
    async def invoke(self, prompt: str, **kwargs: Any) -> str:
        """Generate text for a single prompt."""
        raise NotImplementedError

    async def invoke_batch(
        self, prompts: List[str], **kwargs: Any
    ) -> List[str]:
        """Generate text for multiple prompts (sequential by default)."""
        return [await self.invoke(p, **kwargs) for p in prompts]

    @property
    def model_name(self) -> str:
        return self.model


# ── Concrete wrappers ─────────────────────────────────────────────────────


class LMStudioRestWrapper(BaseLLMWrapper):
    """Wraps LM Studio REST API (OpenAI-compatible chat completions)."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        super().__init__(model)
        self.base_url = (base_url or LMS_BASE_URL).rstrip("/")

    async def invoke(self, prompt: str, **kwargs: Any) -> str:
        client = await _http()
        url = f"{self.base_url}/v1/chat/completions"
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
        }
        log.debug("lmstudio-rest → POST %s model=%s", url, self.model)
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()
        return cast(str, data["choices"][0]["message"]["content"].strip())


class OpenAICompatWrapper(BaseLLMWrapper):
    """Wraps generic OpenAI-compatible API (including remote LM Studio)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        super().__init__(model)
        self.base_url = (base_url or LMS_BASE_URL).rstrip("/")
        self.api_key = api_key or OPENAI_API_KEY or "lm-studio"

    async def invoke(self, prompt: str, **kwargs: Any) -> str:
        client = await _http()
        url = f"{self.base_url}/v1/chat/completions"
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        log.debug("openai-compat → POST %s model=%s", url, self.model)
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return cast(str, data["choices"][0]["message"]["content"].strip())


class OllamaWrapper(BaseLLMWrapper):
    """Wraps Ollama generate API."""

    def __init__(self, host: str | None = None, model: str | None = None):
        super().__init__(model)
        self.host = (host or OLLAMA_HOST).rstrip("/")

    async def invoke(self, prompt: str, **kwargs: Any) -> str:
        client = await _http()
        url = f"{self.host}/api/generate"
        body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
            },
        }
        log.debug("ollama → POST %s model=%s", url, self.model)
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()
        return cast(str, data.get("response", "").strip())


class LMStudioSDKWrapper(BaseLLMWrapper):
    """Wraps LM Studio Python SDK (falls back to REST if SDK unavailable)."""

    def __init__(self, model: str | None = None):
        super().__init__(model)
        self._fallback: Optional[LMStudioRestWrapper] = None

    async def invoke(self, prompt: str, **kwargs: Any) -> str:
        try:
            # SDK is synchronous; run in thread to avoid blocking
            import asyncio

            import lmstudio as lms  # type: ignore[import]

            def _call():
                # Use chat completion via SDK
                chat = lms.Chat()
                chat.add_user_message(prompt)
                prediction = lms.ChatCompletion.create(chat)
                return prediction.content.strip()

            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, _call)
        except ImportError:
            log.warning(
                "lmstudio SDK not installed — falling back to lmstudio-rest"
            )
            if self._fallback is None:
                self._fallback = LMStudioRestWrapper(model=self.model)
            return await self._fallback.invoke(prompt, **kwargs)
        except Exception as e:
            log.warning("SDK failed (%s) — falling back to lmstudio-rest", e)
            if self._fallback is None:
                self._fallback = LMStudioRestWrapper(model=self.model)
            return await self._fallback.invoke(prompt, **kwargs)


# ── Factory ──────────────────────────────────────────────────────────────


BACKEND_MAP = {
    "lmstudio-rest": LMStudioRestWrapper,
    "lmstudio-sdk": LMStudioSDKWrapper,
    "openai-compat": OpenAICompatWrapper,
    "ollama": OllamaWrapper,
}


def create_llm_wrapper(backend: str, **kwargs: Any) -> BaseLLMWrapper:
    """Create an LLM wrapper for the given backend.

    Args:
        backend: One of lmstudio-rest, lmstudio-sdk, openai-compat, ollama.
        **kwargs: Passed to the wrapper constructor (base_url, model, etc.)

    Returns:
        BaseLLMWrapper instance.

    Raises:
        ValueError: For unsupported backend names.
    """
    cls = BACKEND_MAP.get(backend)
    if cls is None:
        raise ValueError(
            f"Unsupported LLM backend: '{backend}'. "
            f"Options: {list(BACKEND_MAP.keys())}"
        )
    return cast(BaseLLMWrapper, cls(**kwargs))


# ── Langchain adapter for RAGAS ─────────────────────────────────────────


class RAGASLLMAdapter:
    """Minimal Langchain-compatible adapter for RAGAS.

    RAGAS 0.2.x expects an object with an ``invoke()`` method that
    accepts a string prompt and returns an ``AIMessage`` (or plain
    string).  This adapter wraps any :class:`BaseLLMWrapper` in that
    interface without requiring a hard dependency on Langchain.

    Usage:
        wrapper = create_llm_wrapper("lmstudio-rest")
        adapter = RAGASLLMAdapter(wrapper)
        result = await adapter.invoke("What is RAG?")
    """

    def __init__(self, wrapper: BaseLLMWrapper):
        self.wrapper = wrapper

    async def invoke(self, prompt: str, **kwargs: Any) -> Any:
        """Generate text and wrap in a Langchain-compatible message object.

        Returns either an ``AIMessage`` (if langchain is installed) or
        a plain dict with ``content`` and ``type`` keys.
        """
        text = await self.wrapper.invoke(prompt, **kwargs)
        # Try to return a real AIMessage if langchain is available
        try:
            from langchain_core.messages import AIMessage

            return AIMessage(content=text)
        except ImportError:
            # Fallback: return a dict that duck-types as an AIMessage
            return {"content": text, "type": "ai"}

    @property
    def model_name(self) -> str:
        return self.wrapper.model_name

    def __repr__(self) -> str:
        return (
            f"RAGASLLMAdapter(wrapper={self.wrapper.__class__.__name__}, "
            f"model={self.model_name})"
        )
