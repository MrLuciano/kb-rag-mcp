"""
Cross-Encoder Reranking for improved search precision.

FASE 12: Search Quality Enhancement

Uses a cross-encoder model to rerank top-k results from vector search,
improving precision and NDCG@5 by scoring query-document pairs directly.
"""

import logging
import os
from typing import Any

log = logging.getLogger("kb-mcp.reranker")

# Configuration
RERANKER_MODEL = os.getenv(
    "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
RERANKER_BATCH_SIZE = int(os.getenv("RERANKER_BATCH_SIZE", "20"))
RERANKER_CACHE_TTL = int(os.getenv("RERANKER_CACHE_TTL", "3600"))


class CrossEncoderReranker:
    """
    Cross-encoder reranker for top-k search results.
    
    Features:
    - Lazy loading (only load model on first use)
    - Batch processing for efficiency
    - Async support (non-blocking)
    - Cache integration ready
    
    Usage:
        reranker = CrossEncoderReranker()
        reranked = await reranker.rerank(query, results, top_k=5)
    """

    def __init__(self):
        self.model: Any = None
        self.model_name = RERANKER_MODEL
        self.batch_size = RERANKER_BATCH_SIZE
        log.info(
            f"CrossEncoderReranker initialized: "
            f"model={self.model_name}, batch_size={self.batch_size}"
        )

    def _load_model(self) -> None:
        """Lazy load cross-encoder model."""
        if self.model is not None:
            return
        
        log.info(f"Loading cross-encoder model: {self.model_name}")
        try:
            from sentence_transformers import CrossEncoder
            
            self.model = CrossEncoder(self.model_name)
            log.info("Cross-encoder model loaded successfully")
        except ImportError as e:
            log.error(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
            raise ImportError(
                "sentence-transformers required for reranking"
            ) from e
        except Exception as e:
            log.error(f"Failed to load cross-encoder model: {e}")
            raise

    async def rerank(
        self,
        query: str,
        results: list[dict],
        top_k: int | None = None,
    ) -> list[dict]:
        """
        Rerank search results using cross-encoder.
        
        Args:
            query: Original search query
            results: List of search results (with 'text' field)
            top_k: Number of results to return (default: all)
        
        Returns:
            Reranked results with updated scores
        """
        if not results:
            return results
        
        log.info(
            f"Reranking {len(results)} results for query: '{query[:50]}...'"
        )
        
        # Lazy load model
        self._load_model()
        
        # Build query-document pairs
        pairs = [(query, result.get("text", "")) for result in results]
        
        # Score pairs in batches
        scores = []
        for i in range(0, len(pairs), self.batch_size):
            batch = pairs[i : i + self.batch_size]
            batch_scores = self.model.predict(batch)
            scores.extend(batch_scores)
        
        # Combine results with new scores
        reranked_results = []
        for result, score in zip(results, scores):
            reranked_result = result.copy()
            reranked_result["score"] = float(score)
            reranked_result["reranked"] = True
            reranked_results.append(reranked_result)
        
        # Sort by new scores (descending)
        reranked_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top_k if specified
        if top_k is not None:
            reranked_results = reranked_results[:top_k]
        
        log.info(f"Reranking complete: returned {len(reranked_results)} results")
        
        return reranked_results

    async def rerank_with_cache(
        self,
        query: str,
        results: list[dict],
        top_k: int | None = None,
        cache_manager: Any = None,
    ) -> list[dict]:
        """
        Rerank with optional cache support.
        
        Args:
            query: Search query
            results: Search results
            top_k: Number of results to return
            cache_manager: Optional cache manager instance
        
        Returns:
            Reranked results (from cache or freshly computed)
        """
        # Generate cache key from query + result IDs
        if cache_manager is not None:
            result_ids = [r.get("id", r.get("chunk_id", "")) for r in results]
            cache_key = f"rerank:{hash(query)}:{hash(tuple(result_ids))}"
            
            # Check cache
            cached = await cache_manager.get(cache_key)
            if cached is not None:
                log.info(f"Reranking cache hit for key: {cache_key}")
                return cached
        
        # Compute reranking
        reranked = await self.rerank(query, results, top_k)
        
        # Store in cache
        if cache_manager is not None:
            await cache_manager.set(
                cache_key, reranked, ttl=RERANKER_CACHE_TTL
            )
        
        return reranked


# Global instance (lazy loaded)
_reranker: CrossEncoderReranker | None = None


def get_reranker() -> CrossEncoderReranker:
    """Get or create global reranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker
