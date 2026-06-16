"""Unit tests for IR metric computation.

FASE 25: Optimization Experiments
"""

import pytest

from kb_server.optimization.metric_computer import (
    MetricComputer,
    mean_reciprocal_rank,
    ndcg_at_k,
    recall_at_k,
)

pytestmark = pytest.mark.fase25


# ── recall@k tests ────────────────────────────────────────────────


class TestRecallAtK:
    def test_recall_at_k_perfect(self):
        """All expected docs in top-k -> 1.0"""
        retrieved = ["a", "b", "c"]
        expected = ["a", "b"]
        assert recall_at_k(retrieved, expected, k=3) == 1.0

    def test_recall_at_k_zero(self):
        """No expected docs in top-k -> 0.0"""
        retrieved = ["x", "y", "z"]
        expected = ["a", "b"]
        assert recall_at_k(retrieved, expected, k=3) == 0.0

    def test_recall_at_k_partial(self):
        """2 expected, 1 found in top-3 -> 0.5"""
        retrieved = ["a", "x", "b"]
        expected = ["a", "c"]
        assert recall_at_k(retrieved, expected, k=3) == 0.5

    def test_recall_at_k_empty_expected(self):
        """Empty expected list -> 0.0 (no division by zero)"""
        retrieved = ["a", "b"]
        expected = []
        assert recall_at_k(retrieved, expected, k=2) == 0.0


# ── MRR tests ──────────────────────────────────────────────────────


class TestMeanReciprocalRank:
    def test_mrr_first_position(self):
        """Relevant doc at rank 1 -> 1.0"""
        retrieved = [["a", "b", "c"]]
        expected = [["a"]]
        assert mean_reciprocal_rank(retrieved, expected) == 1.0

    def test_mrr_second_position(self):
        """Relevant doc at rank 2 -> 0.5"""
        retrieved = [["x", "a", "b"]]
        expected = [["a"]]
        assert mean_reciprocal_rank(retrieved, expected) == 0.5

    def test_mrr_no_relevant(self):
        """No relevant docs -> 0.0"""
        retrieved = [["x", "y", "z"]]
        expected = [["a"]]
        assert mean_reciprocal_rank(retrieved, expected) == 0.0

    def test_mrr_multiple_queries(self):
        """Averages correctly across multiple queries"""
        retrieved = [
            ["a", "b", "c"],  # RR = 1.0
            ["x", "a", "b"],  # RR = 0.5
            ["x", "y", "z"],  # RR = 0.0
        ]
        expected = [
            ["a"],
            ["a"],
            ["a"],
        ]
        expected_mrr = (1.0 + 0.5 + 0.0) / 3
        assert mean_reciprocal_rank(retrieved, expected) == expected_mrr


# ── NDCG tests ─────────────────────────────────────────────────────


class TestNDCGAtK:
    def test_ndcg_at_k_perfect(self):
        """Perfect relevance -> > 0.9"""
        relevance = [[1.0, 1.0, 0.0, 0.0, 0.0]]
        scores = [[0.9, 0.8, 0.7, 0.6, 0.5]]
        result = ndcg_at_k(relevance, scores, k=5)
        assert result > 0.9

    def test_ndcg_at_k_zero(self):
        """All zero relevance -> 0.0"""
        relevance = [[0.0, 0.0, 0.0]]
        scores = [[0.5, 0.4, 0.3]]
        assert ndcg_at_k(relevance, scores, k=3) == 0.0


# ── MetricComputer.compute_all tests ───────────────────────────────


class TestMetricComputer:
    def test_compute_all(self):
        """Mock query_results + expected_docs, verify all three metrics."""
        query_results = [
            {
                "query": "q1",
                "retrieved_docs": ["a", "b", "c"],
                "expected_docs": ["a", "d"],
            },
            {
                "query": "q2",
                "retrieved_docs": ["x", "a", "b"],
                "expected_docs": ["a"],
            },
        ]
        computer = MetricComputer()
        result = computer.compute_all(query_results, k=3)

        assert "recall_at_k" in result
        assert "mrr" in result
        assert "ndcg_at_k" in result

        # q1: 1 of 2 expected found in top-3 -> 0.5
        # q2: 1 of 1 expected found at rank 2 -> 1.0
        # avg recall = 0.75
        assert result["recall_at_k"] == 0.75

        # q1: first relevant at rank 1 -> 1.0
        # q2: first relevant at rank 2 -> 0.5
        # mrr = 0.75
        assert result["mrr"] == 0.75

        # NDCG should be positive
        assert 0.0 <= result["ndcg_at_k"] <= 1.0

    def test_compute_all_empty(self):
        """Empty query_results -> all zeros."""
        computer = MetricComputer()
        result = computer.compute_all([])
        assert result == {
            "recall_at_k": 0.0,
            "mrr": 0.0,
            "ndcg_at_k": 0.0,
        }
