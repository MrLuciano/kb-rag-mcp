"""
Embedding client com suporte a múltiplos backends:
  - lmstudio-sdk   → SDK nativo do LM Studio (só funciona se LM Studio
                     estiver na MESMA máquina ou acessível via LMS_HOST)
  - lmstudio-rest  → REST API própria do LM Studio: POST /api/v0/embeddings
  - openai-compat  → API compatível OpenAI: POST /v1/embeddings
                     RECOMENDADO para LM Studio remoto (outro IP na rede)
  - ollama         → Ollama native (recommended for LXC Server / Linux)

Selecione via variável de ambiente EMBED_BACKEND.

IMPORTANTE — URLs esperadas por backend:
  lmstudio-sdk:   LMS_HOST=<LM_STUDIO_HOST>  LMS_PORT=1234  (sem path)
  lmstudio-rest:  LMS_BASE_URL=http://<LM_STUDIO_HOST>:1234  (sem /api ou /v*)
  openai-compat:  LMS_BASE_URL=http://<LM_STUDIO_HOST>:1234  (sem /v1)
  ollama:         OLLAMA_HOST=http://localhost:11434
"""

# Recommended embedding models (via LM Studio or Ollama):
#   - nomic-embed-text v1.5  — balanced, multilingual, MIT license (768-dim)
#   - mxbai-embed-large-v1   — fast on CPU, MTEB top-10 (1024-dim)
#   - bge-m3                 — best quality, dense+sparse unified (1024-dim)

import asyncio
import logging
import os
import re
from typing import Optional

import httpx

from observability.metrics import MetricsCollector
from kb_server.cache.manager import CacheManager

log = logging.getLogger("kb-mcp.embed")

# ── Config
BACKEND = os.getenv("EMBED_BACKEND", "openai-compat")
MODEL = os.getenv(
    "EMBED_MODEL", "text-embedding-nomic-embed-text-v1.5-embedding"
)
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# LMS_BASE_URL: aceita qualquer forma que o usuário colocar e normaliza
# e.g.: http://<LM_STUDIO_HOST>:1234/api/v1  →  http://<LM_STUDIO_HOST>:1234
_raw_lms_url = os.getenv("LMS_BASE_URL", "http://localhost:1234")
LMS_BASE_URL = re.sub(r"/(api/v\d+|v\d+)/?$", "", _raw_lms_url).rstrip("/")

# Para o SDK nativo, extrai host e porta separados
_lms_match = re.match(r"https?://([^:/]+)(?::(\d+))?", LMS_BASE_URL)
if _lms_match is not None:
    LMS_HOST = os.getenv("LMS_HOST", _lms_match.group(1))
    LMS_PORT = int(os.getenv("LMS_PORT", _lms_match.group(2) or "1234"))
else:
    LMS_HOST = os.getenv("LMS_HOST", "localhost")
    LMS_PORT = int(os.getenv("LMS_PORT", "1234"))

# dimensões conhecidas por modelo (nome completo ou curto)
KNOWN_DIMS = {
    "nomic-embed-text-v1.5": 768,
    "text-embedding-nomic-embed-text-v1.5-embedding": 768,
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    "text-embedding-3-small": 1536,
    "nomic-embed-code": 768,
}

# ── Connection pool config (FASE 8)
HTTP_POOL_CONNECTIONS = int(os.getenv("HTTP_POOL_CONNECTIONS", "20"))
HTTP_POOL_MAXSIZE = int(os.getenv("HTTP_POOL_MAXSIZE", "50"))
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "60.0"))
BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "32"))

# ── Cache do cliente httpx e embedding cache
_http_client: httpx.AsyncClient | None = None
_embed_cache: Optional[CacheManager] = None
_metrics: Optional[MetricsCollector] = None


def init_cache(
    cache_manager: Optional[CacheManager] = None,
    metrics: Optional[MetricsCollector] = None,
) -> None:
    """
    Initialize embedding cache and metrics.

    Args:
        cache_manager: CacheManager instance (creates default if None)
        metrics: MetricsCollector instance (optional)
    """
    global _embed_cache, _metrics
    if cache_manager is None:
        # Default: LRU with 512 MB, 1 hour TTL
        cache_manager = CacheManager(
            backend="lru",
            max_size_mb=512,
            default_ttl=3600,
            metrics=metrics,
        )
    _embed_cache = cache_manager
    _metrics = metrics
    log.info(
        "Embedding cache initialized: backend=%s",
        cache_manager.backend_type,
    )


async def _http() -> httpx.AsyncClient:
    """
    Get or create HTTP client with connection pooling.
    
    FASE 8: Enhanced with connection pooling for better throughput.
    Limits configured via HTTP_POOL_* environment variables.
    """
    global _http_client
    if _http_client is None:
        limits = httpx.Limits(
            max_connections=HTTP_POOL_MAXSIZE,
            max_keepalive_connections=HTTP_POOL_CONNECTIONS,
            keepalive_expiry=30.0,
        )
        _http_client = httpx.AsyncClient(
            timeout=HTTP_TIMEOUT,
            limits=limits,
            http2=True,  # Enable HTTP/2 for multiplexing
        )
        log.info(
            "HTTP client initialized: pool_size=%d, max_connections=%d, "
            "timeout=%.1fs",
            HTTP_POOL_CONNECTIONS,
            HTTP_POOL_MAXSIZE,
            HTTP_TIMEOUT,
        )
    return _http_client


# ── Backends


async def _embed_lmstudio_sdk(text: str) -> list[float]:
    """
    SDK nativo do LM Studio.
    Requer que o LM Studio daemon esteja acessível via WebSocket.
    Para servidor remoto, configure LMS_HOST e LMS_PORT.
    """
    try:
        import lmstudio as lms  # type: ignore[import]

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()

        def _call():
            # Conecta ao host remoto se não for localhost
            if LMS_HOST not in ("localhost", "127.0.0.1"):
                client = lms.Client(f"ws://{LMS_HOST}:{LMS_PORT}")
                return list(client.embedding.model(MODEL).embed(text))
            else:
                return list(lms.embedding_model(MODEL).embed(text))

        return await loop.run_in_executor(None, _call)

    except ImportError:
        log.warning(
            "lmstudio SDK não instalado — usando openai-compat como fallback"
        )
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
    Funciona com LM Studio local e remoto, Ollama e qualquer
    servidor compatível.
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


async def _embed_openai_compat_batch(
    texts: list[str],
) -> list[list[float]]:
    """
    FASE 8: Native batch embedding via OpenAI-compatible API.
    
    Sends multiple texts in a single API call for better throughput.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors in same order as input
    """
    if not texts:
        return []
    
    client = await _http()
    url = f"{LMS_BASE_URL}/v1/embeddings"
    log.debug(
        f"openai-compat BATCH → POST {url} model={MODEL} texts={len(texts)}"
    )
    
    resp = await client.post(
        url,
        headers={"Authorization": "Bearer lm-studio"},
        json={"model": MODEL, "input": texts},
    )
    resp.raise_for_status()
    
    data = resp.json()["data"]
    # Sort by index to ensure correct order
    sorted_data = sorted(data, key=lambda x: x.get("index", 0))
    return [item["embedding"] for item in sorted_data]


async def _embed_ollama(text: str) -> list[float]:
    """Ollama native — ideal for LXC Server / Linux without GPU."""
    client = await _http()
    resp = await client.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": MODEL, "prompt": text},
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


async def _embed_ollama_batch(texts: list[str]) -> list[list[float]]:
    """
    FASE 8: Batch embedding for Ollama.
    
    Ollama doesn't have native batch API, so we use parallel requests.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    # Ollama doesn't support batch API, use parallel requests
    results = await asyncio.gather(
        *[_embed_ollama(text) for text in texts]
    )
    return list(results)


# ── Dispatcher público

_BACKENDS = {
    "lmstudio-sdk": _embed_lmstudio_sdk,
    "lmstudio-rest": _embed_lmstudio_rest,
    "openai-compat": _embed_openai_compat,
    "ollama": _embed_ollama,
}


async def get_embedding(text: str, use_cache: bool = True) -> list[float]:
    """
    Retorna o vetor de embedding para o texto usando o backend
    configurado.

    Args:
        text: Text to embed
        use_cache: Whether to use cache (default True)

    Returns:
        Embedding vector
    """
    # Check cache first
    if use_cache and _embed_cache is not None:
        cache_key = _embed_cache.hash_key("embed", BACKEND, MODEL, text)
        cached = _embed_cache.get(cache_key)
        if cached is not None:
            log.debug("Cache hit for text (len=%d)", len(text))
            return cached

    fn = _BACKENDS.get(BACKEND)
    if fn is None:
        raise ValueError(
            f"EMBED_BACKEND inválido: '{BACKEND}'. Opções: {list(_BACKENDS)}"
        )

    try:
        vector = await fn(text)
        log.debug(f"Embedding gerado: {len(vector)} dims via {BACKEND}")

        # Cache the result
        if use_cache and _embed_cache is not None:
            cache_key = _embed_cache.hash_key("embed", BACKEND, MODEL, text)
            # Estimate size: len(vector) floats * 8 bytes per float
            size_bytes = len(vector) * 8
            _embed_cache.put(cache_key, vector, size_bytes=size_bytes)

        return vector
    except Exception as e:
        log.error(f"Erro no embedding ({BACKEND}): {e}")
        raise


async def get_embeddings_batch(
    texts: list[str], batch_size: int | None = None, use_cache: bool = True
) -> list[list[float]]:
    """
    FASE 8: Optimized batch embedding with native API support and caching.
    
    Uses native batch APIs when available (openai-compat) for 3-5x speedup.
    Falls back to parallel requests for backends without batch support.
    
    Process flow:
    1. Check cache for all texts
    2. Group uncached texts into batches
    3. Process batches via native API or parallel requests
    4. Cache new results
    5. Return all vectors in original order
    
    Args:
        texts: List of texts to embed
        batch_size: Batch size (default: BATCH_SIZE env var or 32)
        use_cache: Whether to use cache (default True)
        
    Returns:
        List of embedding vectors in same order as input texts
    """
    if not texts:
        return []
    
    if batch_size is None:
        batch_size = BATCH_SIZE
    
    # Step 1: Check cache for all texts
    cache_results: dict[int, list[float]] = {}
    uncached_indices: list[int] = []
    
    if use_cache and _embed_cache is not None:
        for i, text in enumerate(texts):
            cache_key = _embed_cache.hash_key("embed", BACKEND, MODEL, text)
            cached = _embed_cache.get(cache_key)
            if cached is not None:
                cache_results[i] = cached
            else:
                uncached_indices.append(i)
        
        if cache_results:
            log.debug(
                "Batch cache: %d hits, %d misses",
                len(cache_results),
                len(uncached_indices),
            )
            if _metrics:
                _metrics.increment(
                    "embedding_cache_hits_total",
                    len(cache_results),
                )
                _metrics.increment(
                    "embedding_cache_misses_total",
                    len(uncached_indices),
                )
    else:
        uncached_indices = list(range(len(texts)))
    
    # If all cached, return early
    if not uncached_indices:
        return [cache_results[i] for i in range(len(texts))]
    
    # Step 2: Get uncached texts
    uncached_texts = [texts[i] for i in uncached_indices]
    
    # Step 3: Process via native batch API if supported
    if BACKEND == "openai-compat":
        # Use native batch API
        new_vectors: list[list[float]] = []
        for i in range(0, len(uncached_texts), batch_size):
            batch_texts = uncached_texts[i : i + batch_size]
            try:
                batch_vectors = await _embed_openai_compat_batch(batch_texts)
                new_vectors.extend(batch_vectors)
                log.info(
                    "Batch embeddings: %d/%d (native API)",
                    min(i + batch_size, len(uncached_texts)),
                    len(uncached_texts),
                )
            except Exception as e:
                log.warning(
                    "Batch API failed (%s), falling back to parallel: %s",
                    BACKEND,
                    e,
                )
                # Fallback to parallel requests
                batch_vectors = await asyncio.gather(
                    *[get_embedding(t, use_cache=False) for t in batch_texts]
                )
                new_vectors.extend(batch_vectors)
    
    elif BACKEND == "ollama":
        # Ollama: parallel requests in batches
        new_vectors = []
        for i in range(0, len(uncached_texts), batch_size):
            batch_texts = uncached_texts[i : i + batch_size]
            batch_vectors = await _embed_ollama_batch(batch_texts)
            new_vectors.extend(batch_vectors)
            log.info(
                "Batch embeddings: %d/%d (parallel)",
                min(i + batch_size, len(uncached_texts)),
                len(uncached_texts),
            )
    
    else:
        # Other backends: parallel requests
        new_vectors = []
        for i in range(0, len(uncached_texts), batch_size):
            batch_texts = uncached_texts[i : i + batch_size]
            batch_vectors = await asyncio.gather(
                *[get_embedding(t, use_cache=False) for t in batch_texts]
            )
            new_vectors.extend(batch_vectors)
            log.info(
                "Batch embeddings: %d/%d (parallel)",
                min(i + batch_size, len(uncached_texts)),
                len(uncached_texts),
            )
    
    # Step 4: Cache new results
    if use_cache and _embed_cache is not None:
        for i, vector in zip(uncached_indices, new_vectors):
            text = texts[i]
            cache_key = _embed_cache.hash_key("embed", BACKEND, MODEL, text)
            size_bytes = len(vector) * 8
            _embed_cache.put(cache_key, vector, size_bytes=size_bytes)
    
    # Step 5: Merge cached and new results in original order
    all_results: dict[int, list[float]] = {**cache_results}
    for i, vector in zip(uncached_indices, new_vectors):
        all_results[i] = vector
    
    return [all_results[i] for i in range(len(texts))]


def get_embed_dim() -> int:
    """Retorna a dimensão esperada do modelo configurado."""
    dim = KNOWN_DIMS.get(MODEL, 768)
    log.debug("Embed dim for model '%s': %d", MODEL, dim)
    return dim


def get_cache_stats() -> dict:
    """Return cache statistics."""
    if _embed_cache is None:
        log.debug("Cache stats: disabled")
        return {"status": "disabled"}
    stats = _embed_cache.stats()
    log.debug("Cache stats: %s", stats)
    return stats


async def close() -> None:
    """
    FASE 8: Cleanup resources (HTTP client, connections).
    
    Call this on server shutdown to gracefully close connections.
    """
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        log.info("HTTP client closed")


async def health_check() -> dict:
    """Verifica se o backend de embedding está respondendo."""
    try:
        vec = await get_embedding("health check")
        log.info("Embedding health check OK: backend=%s model=%s dims=%d", BACKEND, MODEL, len(vec))
        return {
            "status": "ok",
            "backend": BACKEND,
            "model": MODEL,
            "dims": len(vec),
        }
    except Exception as e:
        log.warning("Embedding health check FAILED: %s", e)
        return {"status": "error", "backend": BACKEND, "error": str(e)}
