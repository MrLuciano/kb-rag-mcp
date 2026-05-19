"""
Retrieval module for search quality enhancements (FASE 12).

Modules:
- hybrid_search: Combine dense + BM25 sparse with RRF fusion
- reranker: Cross-encoder reranking for top results
"""

from kb_server.retrieval.hybrid_search import (
    HybridSearcher,
    get_hybrid_searcher,
)
from kb_server.retrieval.reranker import (
    CrossEncoderReranker,
    get_reranker,
)

__all__ = [
    "HybridSearcher",
    "get_hybrid_searcher",
    "CrossEncoderReranker",
    "get_reranker",
]
