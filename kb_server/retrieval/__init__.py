"""
Retrieval module for search quality enhancements (PHASE 12).

Modules:
- hybrid_search: Combine dense + BM25 sparse with RRF fusion
- reranker: Cross-encoder reranking for top results
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kb_server.retrieval.hybrid_search import HybridSearcher
    from kb_server.retrieval.reranker import CrossEncoderReranker

__all__ = [
    "HybridSearcher",
    "get_hybrid_searcher",
    "CrossEncoderReranker",
    "get_reranker",
]


def get_hybrid_searcher():
    """Lazy loader for hybrid searcher to avoid importing heavy deps at startup."""
    from kb_server.retrieval.hybrid_search import get_hybrid_searcher as _impl
    return _impl()


def get_reranker():
    """Lazy loader for reranker to avoid importing heavy deps at startup."""
    from kb_server.retrieval.reranker import get_reranker as _impl
    return _impl()
