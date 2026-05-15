"""
Embedding client com suporte a múltiplos backends:
  - lmstudio-sdk   → SDK nativo do LM Studio (só funciona se LM Studio
                     estiver na MESMA máquina ou acessível via LMS_HOST)
  - lmstudio-rest  → REST API própria do LM Studio: POST /api/v0/embeddings
  - openai-compat  → API compatível OpenAI: POST /v1/embeddings
                     RECOMENDADO para LM Studio remoto (outro IP na rede)
  - ollama         → Ollama nativo (recomendado para Proxmox/Linux)

Selecione via variável de ambiente EMBED_BACKEND.

IMPORTANTE — URLs esperadas por backend:
  lmstudio-sdk:   LMS_HOST=192.168.1.177  LMS_PORT=1234  (sem path)
  lmstudio-rest:  LMS_BASE_URL=http://192.168.1.177:1234  (sem /api ou /v*)
  openai-compat:  LMS_BASE_URL=http://192.168.1.177:1234  (sem /v1)
  ollama:         OLLAMA_HOST=http://localhost:11434
"""

import asyncio
import logging
import os
import re

import httpx

log = logging.getLogger("kb-mcp.embed")

# ── Config ────────────────────────────────────────────────────────────────────
BACKEND    = os.getenv("EMBED_BACKEND", "openai-compat")
MODEL      = os.getenv("EMBED_MODEL", "text-embedding-nomic-embed-text-v1.5-embedding")
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# LMS_BASE_URL: aceita qualquer forma que o usuário colocar e normaliza
# ex: http://192.168.1.177:1234/api/v1  →  http://192.168.1.177:1234
_raw_lms_url = os.getenv("LMS_BASE_URL", "http://localhost:1234")
LMS_BASE_URL = re.sub(r"/(api/v\d+|v\d+)/?$", "", _raw_lms_url).rstrip("/")

# Para o SDK nativo, extrai host e porta separados
_lms_match   = re.match(r"https?://([^:/]+)(?::(\d+))?", LMS_BASE_URL)
LMS_HOST     = os.getenv("LMS_HOST", _lms_match.group(1) if _lms_match else "localhost")
LMS_PORT     = int(os.getenv("LMS_PORT", _lms_match.group(2) or "1234"))

# dimensões conhecidas por modelo (nome completo ou curto)
KNOWN_DIMS = {
    "nomic-embed-text-v1.5":                          768,
    "text-embedding-nomic-embed-text-v1.5-embedding": 768,
    "nomic-embed-text":                               768,
    "mxbai-embed-large":                              1024,
    "text-embedding-3-small":                         1536,
    "nomic-embed-code":                               768,
}

# ── Cache do cliente httpx ────────────────────────────────────────────────────
_http_client: httpx.AsyncClient | None = None

async def _http() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


# ── Backends ──────────────────────────────────────────────────────────────────

async def _embed_lmstudio_sdk(text: str) -> list[float]:
    """
    SDK nativo do LM Studio.
    Requer que o LM Studio daemon esteja acessível via WebSocket.
    Para servidor remoto, configure LMS_HOST e LMS_PORT.
    """
    try:
        import lmstudio as lms
        loop = asyncio.get_event_loop()

        def _call():
            # Conecta ao host remoto se não for localhost
            if LMS_HOST not in ("localhost", "127.0.0.1"):
                client = lms.Client(f"ws://{LMS_HOST}:{LMS_PORT}")
                return list(client.embedding.model(MODEL).embed(text))
            else:
                return list(lms.embedding_model(MODEL).embed(text))

        return await loop.run_in_executor(None, _call)

    except ImportError:
        log.warning("lmstudio SDK não instalado — usando openai-compat como fallback")
        return await _embed_openai_compat(text)
    except Exception as e:
        log.warning(f"SDK falhou ({e}) — usando openai-compat como fallback")
        return await _embed_openai_compat(text)


async def _embed_lmstudio_rest(text: str) -> list[float]:
    """
    REST API própria do LM Studio: POST /api/v0/embeddings
    LMS_BASE_URL deve ser apenas http://host:porta (sem path)
    """
    client = await _http()
    url = f"{LMS_BASE_URL}/api/v0/embeddings"
    log.debug(f"lmstudio-rest → POST {url}")
    resp = await client.post(url, json={"model": MODEL, "input": text})
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


async def _embed_openai_compat(text: str) -> list[float]:
    """
    API compatível com OpenAI: POST /v1/embeddings
    Funciona com LM Studio local e remoto, Ollama e qualquer servidor compatível.
    LMS_BASE_URL deve ser apenas http://host:porta (sem /v1)
    """
    client = await _http()
    url = f"{LMS_BASE_URL}/v1/embeddings"
    log.debug(f"openai-compat → POST {url} model={MODEL}")
    resp = await client.post(
        url,
        headers={"Authorization": "Bearer lm-studio"},
        json={"model": MODEL, "input": [text]},
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


async def _embed_ollama(text: str) -> list[float]:
    """Ollama nativo — ideal para Proxmox/Linux sem GPU."""
    client = await _http()
    resp = await client.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": MODEL, "prompt": text},
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


# ── Dispatcher público ────────────────────────────────────────────────────────

_BACKENDS = {
    "lmstudio-sdk":  _embed_lmstudio_sdk,
    "lmstudio-rest": _embed_lmstudio_rest,
    "openai-compat": _embed_openai_compat,
    "ollama":        _embed_ollama,
}


async def get_embedding(text: str) -> list[float]:
    """Retorna o vetor de embedding para o texto usando o backend configurado."""
    fn = _BACKENDS.get(BACKEND)
    if fn is None:
        raise ValueError(f"EMBED_BACKEND inválido: '{BACKEND}'. Opções: {list(_BACKENDS)}")

    try:
        vector = await fn(text)
        log.debug(f"Embedding gerado: {len(vector)} dims via {BACKEND}")
        return vector
    except Exception as e:
        log.error(f"Erro no embedding ({BACKEND}): {e}")
        raise


async def get_embeddings_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Processa uma lista de textos em batches para não sobrecarregar o servidor."""
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_results = await asyncio.gather(*[get_embedding(t) for t in batch])
        results.extend(batch_results)
        log.info(f"Embeddings: {min(i + batch_size, len(texts))}/{len(texts)}")
    return results


def get_embed_dim() -> int:
    """Retorna a dimensão esperada do modelo configurado."""
    return KNOWN_DIMS.get(MODEL, 768)


async def health_check() -> dict:
    """Verifica se o backend de embedding está respondendo."""
    try:
        vec = await get_embedding("health check")
        return {"status": "ok", "backend": BACKEND, "model": MODEL, "dims": len(vec)}
    except Exception as e:
        return {"status": "error", "backend": BACKEND, "error": str(e)}
