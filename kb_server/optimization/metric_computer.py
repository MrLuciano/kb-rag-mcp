"""Deterministic IR metric computation for optimization experiments.

PHASE 25: Optimization Experiments

Provides recall@K, MRR, and NDCG via sklearn.  All metrics are
pure-Python and require no external services (Qdrant, LLM, etc.).
"""

import logging
from typing import List, Optional

import numpy as np
from sklearn.metrics import ndcg_score

log = logging.getLogger("kb-mcp.optimization")


# ── Standalone metric functions ────────────────────────────────────


def recall_at_k(
    retrieved_docs: List[str],
    expected_docs: List[str],
    k: int = 5,
) -> float:
    """Fraction of expected documents found in the top-k retrieved docs.

    Args:
        retrieved_docs: Ordered list of retrieved document identifiers.
        expected_docs: List of expected (relevant) document identifiers.
        k: Cut-off rank for evaluation.

    Returns:
        Recall@K score in [0.0, 1.0].  Returns 0.0 when *expected_docs*
        is empty to avoid division by zero.
    """
    if not expected_docs:
        return 0.0

    top_k = retrieved_docs[:k]
    found = sum(1 for doc in expected_docs if doc in top_k)
    return found / len(expected_docs)


def mean_reciprocal_rank(
    retrieved_docs_per_query: List[List[str]],
    expected_docs_per_query: List[List[str]],
) -> float:
    """Standard Mean Reciprocal Rank (MRR).

    For each query, the reciprocal rank is ``1 / rank`` of the first
    relevant document.  MRR is the mean of these values across all
    queries.

    Args:
        retrieved_docs_per_query: List of retrieved doc lists, one per
            query.
        expected_docs_per_query: List of expected doc lists, one per
            query.

    Returns:
        MRR score in [0.0, 1.0].  Returns 0.0 when no queries are
        provided.
    """
    if not retrieved_docs_per_query:
        return 0.0

    rr_sum = 0.0
    for retrieved, expected in zip(
        retrieved_docs_per_query, expected_docs_per_query
    ):
        for rank, doc in enumerate(retrieved, start=1):
            if doc in expected:
                rr_sum += 1.0 / rank
                break

    return rr_sum / len(retrieved_docs_per_query)


def ndcg_at_k(
    relevance_scores: List[List[float]],
    retrieved_scores: List[List[float]],
    k: int = 5,
) -> float:
    """Normalized Discounted Cumulative Gain at rank *k*.

    Wraps :func:`sklearn.metrics.ndcg_score` with binary relevance.
    Each inner list corresponds to one query.

    Args:
        relevance_scores: List of relevance lists (1 = relevant, 0 = not)
            per query.
        retrieved_scores: List of retrieval confidence scores per query.
        k: Cut-off rank for evaluation.

    Returns:
        Average NDCG@K across queries in [0.0, 1.0].  Returns 0.0 when
        no queries are provided.
    """
    if not relevance_scores:
        return 0.0

    scores = []
    for rel, ret in zip(relevance_scores, retrieved_scores):
        if not rel:
            scores.append(0.0)
            continue
        rel_arr = np.asarray([rel])
        ret_arr = np.asarray([ret])
        try:
            scores.append(float(ndcg_score(rel_arr, ret_arr, k=k)))
        except Exception:
            scores.append(0.0)

    return sum(scores) / len(scores) if scores else 0.0


# ── MetricComputer class ───────────────────────────────────────────


class MetricComputer:
    """Compute IR metrics for a batch of query results.

    This class is a thin wrapper around the standalone module-level
    functions.  It is provided for convenience when the caller prefers
    an object-oriented interface.
    """

    def recall_at_k(
        self,
        retrieved_docs: List[str],
        expected_docs: List[str],
        k: int = 5,
    ) -> float:
        """See :func:`recall_at_k`."""
        return recall_at_k(retrieved_docs, expected_docs, k)

    def mean_reciprocal_rank(
        self,
        retrieved_docs_per_query: List[List[str]],
        expected_docs_per_query: List[List[str]],
    ) -> float:
        """See :func:`mean_reciprocal_rank`."""
        return mean_reciprocal_rank(
            retrieved_docs_per_query, expected_docs_per_query
        )

    def ndcg_at_k(
        self,
        relevance_scores: List[List[float]],
        retrieved_scores: List[List[float]],
        k: int = 5,
    ) -> float:
        """See :func:`ndcg_at_k`."""
        return ndcg_at_k(relevance_scores, retrieved_scores, k)

    def compute_all(
        self,
        query_results: List[dict],
        dataset: Optional[object] = None,
        k: int = 5,
    ) -> dict:
        """Run recall@k, MRR, and NDCG for a full experiment run.

        Args:
            query_results: List of result dicts, each with keys:
                ``query`` (str), ``retrieved_docs`` (list of str),
                ``expected_docs`` (list of str).
            dataset: Optional ``GoldenDataset`` instance (unused but
                kept for API compatibility).
            k: Cut-off rank for evaluation.

        Returns:
            Dictionary with keys ``recall_at_k``, ``mrr``,
            ``ndcg_at_k`` mapped to float scores.
        """
        if not query_results:
            return {"recall_at_k": 0.0, "mrr": 0.0, "ndcg_at_k": 0.0}

        # recall@k
        recall_scores = []
        for qr in query_results:
            recall_scores.append(
                recall_at_k(
                    qr.get("retrieved_docs", []),
                    qr.get("expected_docs", []),
                    k=k,
                )
            )
        avg_recall = sum(recall_scores) / len(recall_scores)

        # mrr
        mrr = mean_reciprocal_rank(
            [qr.get("retrieved_docs", []) for qr in query_results],
            [qr.get("expected_docs", []) for qr in query_results],
        )

        # ndcg@k — binary relevance (1 if doc in expected, 0 otherwise)
        relevance_scores = []
        retrieved_scores = []
        for qr in query_results:
            retrieved = qr.get("retrieved_docs", [])[:k]
            expected = set(qr.get("expected_docs", []))
            rel = [1.0 if doc in expected else 0.0 for doc in retrieved]
            # Use descending ranks as scores for NDCG
            scores = [float(k - i) for i in range(len(retrieved))]
            relevance_scores.append(rel)
            retrieved_scores.append(scores)

        ndcg = ndcg_at_k(relevance_scores, retrieved_scores, k=k)

        return {
            "recall_at_k": round(avg_recall, 4),
            "mrr": round(mrr, 4),
            "ndcg_at_k": round(ndcg, 4),
        }
