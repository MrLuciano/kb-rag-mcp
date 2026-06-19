"""
Multi-backend embedding client:
  - lmstudio-sdk   → Native LM Studio SDK (only works if LM Studio
                     is on the SAME machine or accessible via LMS_HOST)
  - lmstudio-rest  → LM Studio REST API: POST /api/v0/embeddings
  - openai-compat  → OpenAI-compatible API: POST /v1/embeddings
                     RECOMMENDED for remote LM Studio (different IP on network)
  - ollama         → Ollama native (recommended for LXC Server / Linux)

Select via the EMBED_BACKEND environment variable.

IMPORTANT — Expected URLs by backend:
  lmstudio-sdk:   LMS_HOST=<LM_STUDIO_HOST>  LMS_PORT=1234  (no path)
  lmstudio-rest:  LMS_BASE_URL=http://<LM_STUDIO_HOST>:1234  (no /api or /v*)
  openai-compat:  LMS_BASE_URL=http://<LM_STUDIO_HOST>:1234  (no /v1)
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
import time
from typing import TYPE_CHECKING, Optional, cast

import httpx

from kb_server.cache.manager import CacheManager
from kb_server.circuit_breaker import CircuitBreaker, CircuitState
from kb_server.provider_budget import ProviderBudget

try:
    from observability.metrics import MetricsCollector, record_batch_embedding
except ImportError:
    MetricsCollector = None  # type: ignore[assignment,misc]
    def record_batch_embedding(*args: object, **kwargs: object) -> None:  # type: ignore[misc]
        pass

if TYPE_CHECKING:
    from kb_server.config.loader import ConfigLoader

log = logging.getLogger("kb-mcp.embed")

# ── Config
BACKEND = os.getenv("EMBED_BACKEND", "openai-compat")
MODEL = os.getenv(
    "EMBED_MODEL", "text-embedding-nomic-embed-text-v1.5-embedding"
)
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# ── Provider resilience config (PHASE 36)
# Fallback chain: semicolon-separated provider names in priority order.
# If the primary provider fails (circuit open, budget exhausted, or error),
# the client falls back to the next provider in the chain.
PROVIDER_CHAIN = [p.strip() for p in BACKEND.split(";") if p.strip()]
PRIMARY_BACKEND = PROVIDER_CHAIN[0] if PROVIDER_CHAIN else BACKEND

# Circuit breaker config
CB_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
CB_COOLDOWN_BASE = float(os.getenv("CIRCUIT_BREAKER_COOLDOWN", "30.0"))
CB_COOLDOWN_MAX = float(os.getenv("CIRCUIT_BREAKER_COOLDOWN_MAX", "300.0"))

# Provider budget config
PB_WINDOW = float(os.getenv("PROVIDER_BUDGET_WINDOW_SECONDS", "60.0"))
PB_MAX_REQUESTS = int(os.getenv("PROVIDER_BUDGET_MAX_REQUESTS", "100"))

# ── Module-level resilience instances
_circuit_breaker = CircuitBreaker(
    failure_threshold=CB_THRESHOLD,
    cooldown_base=CB_COOLDOWN_BASE,
    cooldown_max=CB_COOLDOWN_MAX,
)
_provider_budget = ProviderBudget(
    window_seconds=PB_WINDOW,
    max_requests=PB_MAX_REQUESTS,
)

# LMS_BASE_URL: accepts any user input and normalizes it
# e.g.: http://<LM_STUDIO_HOST>:1234/api/v1  →  http://<LM_STUDIO_HOST>:1234
_raw_lms_url = os.getenv("LMS_BASE_URL", "http://localhost:1234")
LMS_BASE_URL = re.sub(r"/(api/v\d+|v\d+)/?$", "", _raw_lms_url).rstrip("/")

# For the native SDK, extract host and port separately
_lms_match = re.match(r"https?://([^:/]+)(?::(\d+))?", LMS_BASE_URL)
if _lms_match is not None:
    LMS_HOST = os.getenv("LMS_HOST", _lms_match.group(1))
    LMS_PORT = int(os.getenv("LMS_PORT", _lms_match.group(2) or "1234"))
else:
    LMS_HOST = os.getenv("LMS_HOST", "localhost")
    LMS_PORT = int(os.getenv("LMS_PORT", "1234"))

# known dimensions by model (full name or short)
KNOWN_DIMS = {
    "nomic-embed-text-v1.5": 768,
    "text-embedding-nomic-embed-text-v1.5-embedding": 768,
    "nomic-embed-text": 768,
    "nomic-embed-text:v1.5": 768,
    "mxbai-embed-large": 1024,
    "text-embedding-3-small": 1536,
    "nomic-embed-code": 768,
}

# ── Connection pool config (PHASE 8)
HTTP_POOL_CONNECTIONS = int(os.getenv("HTTP_POOL_CONNECTIONS", "20"))
HTTP_POOL_MAXSIZE = int(os.getenv("HTTP_POOL_MAXSIZE", "50"))
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "60.0"))
BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "32"))

# ── HTTP client and embedding cache
_http_client: httpx.AsyncClient | None = None
_embed_cache: Optional[CacheManager] = None
_metrics: Optional[MetricsCollector] = None
_config_loader: Optional["ConfigLoader"] = None


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

    PHASE 8: Enhanced with connection pooling for better throughput.
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
    Native LM Studio SDK.
    Requires LM Studio daemon accessible via WebSocket.
    For remote server, set LMS_HOST and LMS_PORT.
    """
    try:
        import lmstudio as lms  # type: ignore[import]

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()

        def _call():
            # Connect to remote host if not localhost
            if LMS_HOST not in ("localhost", "127.0.0.1"):
                client = lms.Client(f"ws://{LMS_HOST}:{LMS_PORT}")
                return list(client.embedding.model(MODEL).embed(text))
            else:
                return list(lms.embedding_model(MODEL).embed(text))

        return await loop.run_in_executor(None, _call)

    except ImportError:
        log.warning(
            "lmstudio SDK not installed — using openai-compat as fallback"
        )
        return await _embed_openai_compat(text)
    except Exception as e:
        log.warning("SDK failed (%s) — using openai-compat as fallback", e)
        return await _embed_openai_compat(text)


async def _embed_lmstudio_rest(text: str) -> list[float]:
    """
    LM Studio REST API: POST /api/v0/embeddings
    LMS_BASE_URL must be just http://host:port (no path)
    """
    client = await _http()
    url = f"{LMS_BASE_URL}/api/v0/embeddings"
    log.debug("lmstudio-rest → POST %s", url)
    resp = await client.post(url, json={"model": MODEL, "input": text})
    resp.raise_for_status()
    return cast(list[float], resp.json()["data"][0]["embedding"])


async def _embed_openai_compat(text: str) -> list[float]:
    """
    OpenAI-compatible API: POST /v1/embeddings
    Works with local and remote LM Studio, Ollama, and any
    compatible server.
    LMS_BASE_URL must be just http://host:port (no /v1)
    """
    client = await _http()
    url = f"{LMS_BASE_URL}/v1/embeddings"
    log.debug("openai-compat → POST %s model=%s", url, MODEL)
    resp = await client.post(
        url,
        headers={"Authorization": "Bearer lm-studio"},
        json={"model": MODEL, "input": [text]},
    )
    resp.raise_for_status()
    return cast(list[float], resp.json()["data"][0]["embedding"])


async def _embed_openai_compat_batch(
    texts: list[str],
) -> list[list[float]]:
    """
    PHASE 8: Native batch embedding via OpenAI-compatible API.

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
        "openai-compat BATCH → POST %s model=%s texts=%d",
        url,
        MODEL,
        len(texts),
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
    return cast(list[float], resp.json()["embedding"])


async def _embed_ollama_batch(texts: list[str]) -> list[list[float]]:
    """
    PHASE 8: Batch embedding for Ollama.

    Ollama doesn't have native batch API, so we use parallel requests.

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    # Ollama doesn't support batch API, use parallel requests
    results = await asyncio.gather(*[_embed_ollama(text) for text in texts])
    return list(results)


# ── Public dispatcher

_BACKENDS = {
    "lmstudio-sdk": _embed_lmstudio_sdk,
    "lmstudio-rest": _embed_lmstudio_rest,
    "openai-compat": _embed_openai_compat,
    "ollama": _embed_ollama,
}


# ── Provider resilience helpers (PHASE 36)


async def _try_provider(provider: str, text: str) -> Optional[list[float]]:
    """
    Attempt to embed text using a single provider.

    Returns the embedding vector on success, or None if the provider is
    blocked (circuit open, budget exhausted) or fails.

    Args:
        provider: Provider name.
        text: Text to embed.

    Returns:
        Embedding vector or None on failure.
    """
    resolved_provider = provider
    if provider not in _BACKENDS:
        alias = await _resolve_alias(provider)
        if alias is not None:
            resolved_provider = alias

    fn = _BACKENDS.get(resolved_provider)
    if fn is None:
        log.warning("Unknown provider '%s' — not in _BACKENDS", provider)
        return None

    # Circuit breaker check
    state = _circuit_breaker.check(provider)
    if state == CircuitState.OPEN:
        log.warning("Circuit OPEN for provider '%s' — skipping", provider)
        if _metrics:
            _metrics.increment(
                "provider_skipped_circuit_open", 1, provider=provider
            )
        return None

    # Budget check
    if not _provider_budget.check_budget(provider):
        log.warning("Budget exhausted for provider '%s' — skipping", provider)
        if _metrics:
            _metrics.increment(
                "provider_skipped_budget_exhausted", 1, provider=provider
            )
        return None

    # Attempt the call
    try:
        vector = await fn(text)
        # Success: record budget usage and circuit success
        _provider_budget.record_request(provider)
        _circuit_breaker.record_success(provider)
        if _metrics:
            _metrics.increment("provider_requests_total", 1, provider=provider)
        return vector
    except Exception as e:
        log.warning(
            "Provider '%s' failed (%s: %s)",
            provider,
            type(e).__name__,
            e,
        )
        new_state = _circuit_breaker.record_failure(provider)
        if _metrics:
            _metrics.increment("provider_errors_total", 1, provider=provider)
            if new_state == CircuitState.OPEN:
                _metrics.increment(
                    "provider_circuit_opened", 1, provider=provider
                )
        return None


async def _dispatch_with_resilience(
    text: str, providers: Optional[list[str]] = None
) -> list[float]:
    """
    Dispatch an embedding request with provider resilience.

    Tries each provider in order. If a provider is blocked by circuit
    breaker, budget exhaustion, or runtime error, falls back to the
    next provider in the chain.

    Args:
        text: Text to embed.
        providers: Provider list (defaults to PROVIDER_CHAIN).

    Returns:
        Embedding vector.

    Raises:
        RuntimeError: If all providers fail.
    """
    chain = providers if providers is not None else PROVIDER_CHAIN

    last_error: Optional[str] = None
    for provider in chain:
        result = await _try_provider(provider, text)
        if result is not None:
            if last_error is not None and _metrics:
                # Record fallback event
                _metrics.increment(
                    "provider_fallbacks_total",
                    1,
                    from_provider=last_error,
                    to_provider=provider,
                )
            return result
        last_error = provider

    raise RuntimeError(
        f"All providers failed for embedding request. "
        f"Providers tried: {chain}"
    )


def validate_providers() -> None:
    """
    Validate that all providers in the chain are known.

    Raises ValueError if any provider in the chain is not registered
    in _BACKENDS. Aliased provider names are accepted without
    validation since they are resolved lazily at runtime.
    """
    for provider in PROVIDER_CHAIN:
        if provider not in _BACKENDS:
            if _config_loader is not None:
                import asyncio

                resolved = asyncio.run(_config_loader.resolve_alias(provider))
                if resolved is not None:
                    continue
            raise ValueError(
                f"Invalid provider: '{provider}'. "
                f"Options: {list(_BACKENDS)}"
            )


def init_alias_resolution(
    loader: "ConfigLoader",
) -> None:
    """Initialize provider alias resolution from ConfigLoader."""
    global _config_loader
    _config_loader = loader
    loader.on_change("provider_alias.*", _on_alias_changed)


def _on_alias_changed(key: str, value: object) -> None:
    log.debug("Provider alias changed: %s = %s", key, value)


async def _resolve_alias(alias_name: str) -> Optional[str]:
    """
    Resolve a provider alias to its canonical name.

    Returns None if alias resolution is not configured or the alias
    does not exist.
    """
    if _config_loader is None:
        return None
    try:
        resolved = await _config_loader.resolve_alias(alias_name)
        if resolved is not None:
            log.debug(
                "Provider alias resolved: %s -> %s", alias_name, resolved
            )
        else:
            log.debug("Provider alias not found: %s", alias_name)
        return resolved
    except Exception:
        log.debug("Provider alias resolution failed: %s", alias_name)
        return None


async def get_embedding(text: str, use_cache: bool = True) -> list[float]:
    """Return embedding vector for the given text using configured backend.

    Checks the embedding cache first before calling the backend.
    Backend selected via EMBED_BACKEND environment variable.

    Supports fallback chains via `EMBED_BACKEND=primary;secondary` —
    if the primary provider is unavailable (circuit open, budget
    exhausted, or error), the next provider in the chain is tried.

    Args:
        text: Text to embed.
        use_cache: Whether to use cache (default True).

    Returns:
        Embedding vector as a list of floats.
    """
    # Check cache first
    if use_cache and _embed_cache is not None:
        cache_key = _embed_cache.hash_key(
            "embed", PRIMARY_BACKEND, MODEL, text
        )
        cached = _embed_cache.get(cache_key)
        if cached is not None:
            log.debug("Cache hit for text (len=%d)", len(text))
            return cast(list[float], cached)

    validate_providers()

    try:
        vector = await _dispatch_with_resilience(text)
        log.debug("Embedding generated: %d dims", len(vector))

        # Cache the result
        if use_cache and _embed_cache is not None:
            cache_key = _embed_cache.hash_key(
                "embed", PRIMARY_BACKEND, MODEL, text
            )
            # Estimate size: len(vector) floats * 8 bytes per float
            size_bytes = len(vector) * 8
            _embed_cache.put(cache_key, vector, size_bytes=size_bytes)

        return vector
    except Exception as e:
        log.error("Embedding error: %s", e)
        raise


async def get_embeddings_batch(
    texts: list[str], batch_size: int | None = None, use_cache: bool = True
) -> list[list[float]]:
    """
    PHASE 8: Optimized batch embedding with native API support and caching.

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

    validate_providers()

    # Step 1: Check cache for all texts
    cache_results: dict[int, list[float]] = {}
    uncached_indices: list[int] = []

    if use_cache and _embed_cache is not None:
        for i, text in enumerate(texts):
            cache_key = _embed_cache.hash_key(
                "embed", PRIMARY_BACKEND, MODEL, text
            )
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
                    "cache_hits",
                    len(cache_results),
                    backend="lru",
                )
                _metrics.increment(
                    "cache_misses",
                    len(uncached_indices),
                    backend="lru",
                )
    else:
        uncached_indices = list(range(len(texts)))

    # If all cached, return early
    if not uncached_indices:
        return [cache_results[i] for i in range(len(texts))]

    # Step 2: Get uncached texts
    uncached_texts = [texts[i] for i in uncached_indices]

    # Step 3: Process via resilient dispatch
    # For batch operations, use parallel dispatch per text
    new_vectors: list[list[float]] = []

    if PRIMARY_BACKEND == "openai-compat" and len(PROVIDER_CHAIN) == 1:
        # Single provider native batch path (existing optimized path)
        for i in range(0, len(uncached_texts), batch_size):
            batch_texts = uncached_texts[i : i + batch_size]
            batch_start = time.time()
            try:
                batch_vectors = await _embed_openai_compat_batch(batch_texts)
                new_vectors.extend(batch_vectors)
                log.info(
                    "Batch embeddings: %d/%d (native API)",
                    min(i + batch_size, len(uncached_texts)),
                    len(uncached_texts),
                )
                # Record budget and success for batch
                _provider_budget.record_request("openai-compat")
                _circuit_breaker.record_success("openai-compat")
                if _metrics:
                    _metrics.increment(
                        "provider_requests_total",
                        len(batch_texts),
                        provider="openai-compat",
                    )
            except Exception as e:
                log.warning(
                    "Batch API failed (%s), falling back to resilient: %s",
                    PRIMARY_BACKEND,
                    e,
                )
                _circuit_breaker.record_failure("openai-compat")
                if _metrics:
                    _metrics.increment(
                        "provider_errors_total", 1, provider="openai-compat"
                    )
                # Fallback to per-text resilient dispatch
                for t in batch_texts:
                    v = await _dispatch_with_resilience(t)
                    new_vectors.append(v)
            finally:
                record_batch_embedding(
                    PRIMARY_BACKEND,
                    len(batch_texts),
                    time.time() - batch_start,
                )
    elif PRIMARY_BACKEND == "ollama" and len(PROVIDER_CHAIN) == 1:
        # Single provider Ollama: parallel requests in batches
        for i in range(0, len(uncached_texts), batch_size):
            batch_texts = uncached_texts[i : i + batch_size]
            batch_start = time.time()
            try:
                batch_vectors = await _embed_ollama_batch(batch_texts)
                new_vectors.extend(batch_vectors)
                log.info(
                    "Batch embeddings: %d/%d (parallel)",
                    min(i + batch_size, len(uncached_texts)),
                    len(uncached_texts),
                )
                _provider_budget.record_request("ollama")
                _circuit_breaker.record_success("ollama")
                if _metrics:
                    _metrics.increment(
                        "provider_requests_total",
                        len(batch_texts),
                        provider="ollama",
                    )
            except Exception as e:
                log.warning(
                    "Ollama batch failed (%s), resilient fallback: %s",
                    e,
                )
                _circuit_breaker.record_failure("ollama")
                if _metrics:
                    _metrics.increment(
                        "provider_errors_total", 1, provider="ollama"
                    )
                for t in batch_texts:
                    v = await _dispatch_with_resilience(t)
                    new_vectors.append(v)
            finally:
                record_batch_embedding(
                    PRIMARY_BACKEND,
                    len(batch_texts),
                    time.time() - batch_start,
                )
    else:
        # Multi-provider or other backends: per-text resilient dispatch
        for i in range(0, len(uncached_texts), batch_size):
            batch_texts = uncached_texts[i : i + batch_size]
            batch_start = time.time()
            for text in batch_texts:
                v = await _dispatch_with_resilience(text)
                new_vectors.append(v)
            log.info(
                "Batch embeddings: %d/%d (resilient dispatch)",
                min(i + batch_size, len(uncached_texts)),
                len(uncached_texts),
            )
            record_batch_embedding(
                PRIMARY_BACKEND,
                len(batch_texts),
                time.time() - batch_start,
            )

    # Step 4: Cache new results
    if use_cache and _embed_cache is not None:
        for i, vector in zip(uncached_indices, new_vectors):
            text = texts[i]
            cache_key = _embed_cache.hash_key(
                "embed", PRIMARY_BACKEND, MODEL, text
            )
            size_bytes = len(vector) * 8
            _embed_cache.put(cache_key, vector, size_bytes=size_bytes)

    # Step 5: Merge cached and new results in original order
    all_results: dict[int, list[float]] = {**cache_results}
    for i, vector in zip(uncached_indices, new_vectors):
        all_results[i] = vector

    return [all_results[i] for i in range(len(texts))]


def get_embed_dim() -> int:
    """Return the expected embedding dimension for the configured model."""
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
    PHASE 8: Cleanup resources (HTTP client, connections).

    Call this on server shutdown to gracefully close connections.
    """
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        log.info("HTTP client closed")


async def health_check() -> dict:
    """Check if the embedding backend is responding."""
    try:
        vec = await get_embedding("health check")
        log.info(
            "Embedding health check OK: backend=%s model=%s dims=%d",
            PRIMARY_BACKEND,
            MODEL,
            len(vec),
        )
        return {
            "status": "ok",
            "backend": PRIMARY_BACKEND,
            "model": MODEL,
            "dims": len(vec),
        }
    except Exception as e:
        log.warning("Embedding health check FAILED: %s", e)
        return {
            "status": "error",
            "backend": PRIMARY_BACKEND,
            "error": str(e),
        }
