"""
Hybrid Search - Combine dense vector search with BM25 sparse retrieval.

FASE 12: Search Quality Enhancement

Uses RRF (Reciprocal Rank Fusion) to combine scores from dense and
sparse retrieval for improved recall on technical terms and exact matches.
"""

import logging
import os
from typing import Any

from fastembed import SparseTextEmbedding

log = logging.getLogger("kb-mcp.hybrid")

# Configuration
HYBRID_DENSE_WEIGHT = float(os.getenv("HYBRID_DENSE_WEIGHT", "0.7"))
HYBRID_SPARSE_WEIGHT = float(os.getenv("HYBRID_SPARSE_WEIGHT", "0.3"))
HYBRID_RRF_K = int(os.getenv("HYBRID_RRF_K", "60"))
HYBRID_SPARSE_MODEL = os.getenv(
    "HYBRID_SPARSE_MODEL", "Qdrant/bm25"
)


class HybridSearcher:
    """
    Hybrid search combining dense vectors with BM25 sparse retrieval.
    
    Features:
    - Dense vector search (semantic similarity)
    - BM25 sparse search (keyword/term matching)
    - RRF score fusion
    - Compatible with all existing filters
    """

    def __init__(self):
        self.sparse_model: SparseTextEmbedding | None = None
        self.dense_weight = HYBRID_DENSE_WEIGHT
        self.sparse_weight = HYBRID_SPARSE_WEIGHT
        self.rrf_k = HYBRID_RRF_K
        log.info(
            f"HybridSearcher initialized: "
            f"dense={self.dense_weight}, sparse={self.sparse_weight}, "
            f"rrf_k={self.rrf_k}"
        )

    def _load_sparse_model(self) -> None:
        """Lazy load sparse embedding model."""
        if self.sparse_model is not None:
            return
        
        log.info(f"Loading sparse model: {HYBRID_SPARSE_MODEL}")
        try:
            self.sparse_model = SparseTextEmbedding(
                model_name=HYBRID_SPARSE_MODEL
            )
            log.info("Sparse model loaded successfully")
        except Exception as e:
            log.error(f"Failed to load sparse model: {e}")
            raise

    async def generate_sparse_vector(self, text: str) -> dict[int, float]:
        """
        Generate BM25 sparse vector for text.
        
        Returns dict mapping token index to score.
        """
        self._load_sparse_model()
        
        try:
            # fastembed returns list of sparse vectors
            result = list(self.sparse_model.embed([text]))
            if not result:
                log.warning("Sparse embedding returned empty result")
                return {}
            
            # Convert sparse vector to dict format
            sparse_vec = result[0]
            
            # sparse_vec is typically a SparseEmbedding with .indices and .values
            if hasattr(sparse_vec, 'indices') and hasattr(sparse_vec, 'values'):
                return dict(zip(sparse_vec.indices, sparse_vec.values))
            elif isinstance(sparse_vec, dict):
                return sparse_vec
            else:
                log.error(
                    f"Unexpected sparse vector format: {type(sparse_vec)}"
                )
                return {}
                
        except Exception as e:
            log.error(f"Failed to generate sparse vector: {e}")
            # Non-fatal: return empty sparse vector, fall back to dense only
            return {}

    async def search(
        self,
        vector_store: Any,  # VectorStore instance
        query_vector: list[float],
        query_text: str,
        top_k: int = 5,
        filter_type: str | None = None,
        product: str | None = None,
        doc_type: str | None = None,
        version: str | None = None,  # FASE 13: Version filter
    ) -> list[dict]:
        """
        Perform hybrid search combining dense and sparse retrieval.
        
        Args:
            vector_store: VectorStore instance
            query_vector: Dense embedding vector
            query_text: Original query text (for sparse)
            top_k: Number of results to return
            filter_type: File type filter
            product: Product filter
            doc_type: Document type filter
            version: Version filter (FASE 13)
        
        Returns:
            List of results sorted by fused score
        """
        log.info(
            f"Hybrid search: query='{query_text[:50]}...', top_k={top_k}"
        )
        
        # Step 1: Dense search (retrieve more for fusion)
        retrieve_k = min(top_k * 4, 50)  # Get 4x results for better fusion
        dense_results = await vector_store.search(
            vector=query_vector,
            top_k=retrieve_k,
            filter_type=filter_type,
            product=product,
            doc_type=doc_type,
            version=version,  # FASE 13: Pass version filter
        )
        
        log.info(f"Dense search returned {len(dense_results)} results")
        
        # Step 2: Generate sparse vector
        sparse_vector = await self.generate_sparse_vector(query_text)
        
        if not sparse_vector:
            log.warning(
                "Sparse vector empty, falling back to dense-only search"
            )
            return dense_results[:top_k]
        
        # Step 3: Sparse search
        # Note: This requires Qdrant to support sparse vectors in the collection
        # For now, we'll implement RRF with dense results only and add TODO
        # for full sparse search implementation when collection is migrated
        
        # TODO: Implement actual sparse search when collection has sparse vectors
        # sparse_results = await vector_store.search_sparse(
        #     sparse_vector=sparse_vector,
        #     top_k=retrieve_k,
        #     filter_type=filter_type,
        #     product=product,
        #     doc_type=doc_type,
        # )
        
        # For now, use weighted dense search as placeholder
        log.info(
            "Sparse search not yet implemented, using dense results only"
        )
        
        # Step 4: RRF fusion (currently with dense only)
        fused_results = self._rrf_fusion(
            dense_results=dense_results,
            sparse_results=[],  # Empty until sparse search implemented
        )
        
        return fused_results[:top_k]

    def _rrf_fusion(
        self,
        dense_results: list[dict],
        sparse_results: list[dict],
    ) -> list[dict]:
        """
        Reciprocal Rank Fusion of dense and sparse results.
        
        RRF score = sum(1 / (k + rank)) for each result list
        where k is a constant (default 60) and rank is 0-indexed.
        
        Args:
            dense_results: Results from dense vector search
            sparse_results: Results from sparse BM25 search
        
        Returns:
            Fused results sorted by combined score
        """
        scores: dict[str, float] = {}
        result_map: dict[str, dict] = {}
        
        # Process dense results
        for rank, result in enumerate(dense_results):
            chunk_id = result["id"]
            rrf_score = 1.0 / (self.rrf_k + rank + 1)
            scores[chunk_id] = scores.get(chunk_id, 0) + (
                rrf_score * self.dense_weight
            )
            result_map[chunk_id] = result
        
        # Process sparse results
        for rank, result in enumerate(sparse_results):
            chunk_id = result["id"]
            rrf_score = 1.0 / (self.rrf_k + rank + 1)
            scores[chunk_id] = scores.get(chunk_id, 0) + (
                rrf_score * self.sparse_weight
            )
            if chunk_id not in result_map:
                result_map[chunk_id] = result
        
        # Sort by fused score
        sorted_ids = sorted(scores.items(), key=lambda x: -x[1])
        
        # Build result list with fused scores
        fused_results = []
        for chunk_id, score in sorted_ids:
            result = result_map[chunk_id].copy()
            result["score"] = score  # Replace with fused score
            result["fusion"] = "rrf"  # Mark as fused result
            fused_results.append(result)
        
        log.info(
            f"RRF fusion: {len(dense_results)} dense + "
            f"{len(sparse_results)} sparse -> {len(fused_results)} fused"
        )
        
        return fused_results


# Global instance (lazy loaded)
_hybrid_searcher: HybridSearcher | None = None


def get_hybrid_searcher() -> HybridSearcher:
    """Get or create global hybrid searcher instance."""
    global _hybrid_searcher
    if _hybrid_searcher is None:
        _hybrid_searcher = HybridSearcher()
    return _hybrid_searcher
