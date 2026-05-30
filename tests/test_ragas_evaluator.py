"""Unit tests for kb_server/evaluation/metrics.py and ragas_pipeline.py.

Uses mocked LLM judge to avoid live backend dependencies.
"""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kb_server.evaluation.dataset import GoldenDataset
from kb_server.evaluation.metrics import _parse_score
from kb_server.evaluation.ragas_pipeline import RAGASEvaluator


# ── _parse_score tests ─────────────────────────────────────────────────────


class TestParseScore:
    def test_decimal(self):
        assert _parse_score("0.85") == pytest.approx(0.85)
        assert _parse_score("The score is 0.72") == pytest.approx(0.72)

    def test_decimal_leading_dot(self):
        assert _parse_score(".85") == pytest.approx(0.85)

    def test_percentage(self):
        assert _parse_score("85%") == pytest.approx(0.85)
        assert _parse_score("Score: 100%") == pytest.approx(1.0)

    def test_keywords(self):
        assert _parse_score("yes") == 1.0
        assert _parse_score("no") == 0.0
        assert _parse_score("high") == 0.8
        assert _parse_score("medium") == 0.5
        assert _parse_score("low") == 0.2
        assert _parse_score("partial") == 0.5

    def test_integer_ten_scale(self):
        assert _parse_score("8") == pytest.approx(0.8)
        assert _parse_score("10") == pytest.approx(1.0)

    def test_integer_binary(self):
        assert _parse_score("1") == 1.0
        assert _parse_score("0") == 0.0

    def test_unparseable_defaults_neutral(self):
        assert _parse_score("foo bar") == 0.5

    def test_clamped_above_one(self):
        assert _parse_score("150%") == 1.0


# ── RAGASEvaluator tests ─────────────────────────────────────────────────


class TestRAGASEvaluatorInit:
    def test_init_with_mock_llm(self, tmp_path):
        dataset = GoldenDataset(tmp_path / "empty.json")
        mock_llm = MagicMock()
        evaluator = RAGASEvaluator(dataset=dataset, llm_provider=mock_llm)
        assert evaluator.dataset is dataset
        assert evaluator.llm is not None

    def test_init_without_llm_uses_env_backend(self, tmp_path):
        dataset = GoldenDataset(tmp_path / "empty.json")
        with patch("kb_server.evaluation.ragas_pipeline.create_llm_wrapper") as mock_create:
            mock_wrapper = MagicMock()
            mock_create.return_value = mock_wrapper
            evaluator = RAGASEvaluator(dataset=dataset)
            mock_create.assert_called_once()


class TestRAGASEvaluatorEvaluate:
    @pytest.mark.asyncio
    async def test_empty_dataset_returns_empty_dict(self, tmp_path):
        dataset = GoldenDataset(tmp_path / "empty.json")
        mock_llm = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.invoke = AsyncMock(return_value="0.5")
        evaluator = RAGASEvaluator(dataset=dataset, llm_provider=mock_llm)
        evaluator.llm = mock_adapter

        results = await evaluator.evaluate()
        assert results == {}

    @pytest.mark.asyncio
    async def test_evaluate_returns_four_metrics(self, tmp_path):
        dataset_path = tmp_path / "dataset.json"
        dataset_path.write_text(json.dumps([
            {
                "query": "How to install?",
                "expected_answer": "Run the installer.",
                "expected_docs": ["Step 1: download", "Step 2: install"],
            }
        ]))
        dataset = GoldenDataset(dataset_path)

        mock_llm = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.invoke = AsyncMock(return_value="0.8")
        evaluator = RAGASEvaluator(dataset=dataset, llm_provider=mock_llm)
        evaluator.llm = mock_adapter

        results = await evaluator.evaluate()

        assert "faithfulness" in results
        assert "answer_relevancy" in results
        assert "context_precision" in results
        assert "context_recall" in results
        assert all(0.0 <= v <= 1.0 for v in results.values())

    @pytest.mark.asyncio
    async def test_evaluate_with_multiple_examples(self, tmp_path):
        dataset_path = tmp_path / "dataset.json"
        dataset_path.write_text(json.dumps([
            {
                "query": "How to install?",
                "expected_answer": "Run the installer.",
                "expected_docs": ["doc1"],
            },
            {
                "query": "How to configure?",
                "expected_answer": "Edit the config file.",
                "expected_docs": ["doc2"],
            },
        ]))
        dataset = GoldenDataset(dataset_path)

        mock_llm = MagicMock()
        mock_adapter = MagicMock()
        # Return different scores for variety
        mock_adapter.invoke = AsyncMock(side_effect=[
            "0.9", "0.8", "0.7", "0.6",  # example 1
            "0.5", "0.4", "0.3", "0.2",  # example 2
        ])
        evaluator = RAGASEvaluator(dataset=dataset, llm_provider=mock_llm)
        evaluator.llm = mock_adapter

        results = await evaluator.evaluate()

        assert results["faithfulness"] == pytest.approx((0.9 + 0.5) / 2)
        assert results["answer_relevancy"] == pytest.approx((0.8 + 0.4) / 2)
        assert results["context_precision"] == pytest.approx((0.7 + 0.3) / 2)
        assert results["context_recall"] == pytest.approx((0.6 + 0.2) / 2)

    @pytest.mark.asyncio
    async def test_evaluate_skips_missing_contexts(self, tmp_path):
        dataset_path = tmp_path / "dataset.json"
        dataset_path.write_text(json.dumps([
            {
                "query": "How to install?",
                "expected_answer": "Run the installer.",
                "expected_docs": [],  # No contexts
            }
        ]))
        dataset = GoldenDataset(dataset_path)

        mock_llm = MagicMock()
        mock_adapter = MagicMock()
        evaluator = RAGASEvaluator(dataset=dataset, llm_provider=mock_llm)
        evaluator.llm = mock_adapter

        results = await evaluator.evaluate()

        # All metrics should be 0.0 because no contexts were available
        assert all(v == 0.0 for v in results.values())

    @pytest.mark.asyncio
    async def test_evaluate_logs_error_but_continues(self, tmp_path):
        dataset_path = tmp_path / "dataset.json"
        dataset_path.write_text(json.dumps([
            {
                "query": "How to install?",
                "expected_answer": "Run the installer.",
                "expected_docs": ["doc1"],
            },
            {
                "query": "How to configure?",
                "expected_answer": "Edit config.",
                "expected_docs": ["doc2"],
            },
        ]))
        dataset = GoldenDataset(dataset_path)

        mock_llm = MagicMock()
        mock_adapter = MagicMock()
        # Fail on first metric of first example, succeed on rest
        mock_adapter.invoke = AsyncMock(side_effect=[
            Exception("LLM timeout"),
            "0.8", "0.7", "0.6",
            "0.5", "0.4", "0.3", "0.2",
        ])
        evaluator = RAGASEvaluator(dataset=dataset, llm_provider=mock_llm)
        evaluator.llm = mock_adapter

        results = await evaluator.evaluate()

        # Only second example contributes to means
        assert results["faithfulness"] == pytest.approx(0.5)


class TestRAGASEvaluatorSaveResults:
    def test_save_results_creates_json(self, tmp_path):
        dataset = GoldenDataset(tmp_path / "empty.json")
        mock_llm = MagicMock()
        evaluator = RAGASEvaluator(dataset=dataset, llm_provider=mock_llm)

        output = tmp_path / "results.json"
        evaluator.save_results({"faithfulness": 0.85}, output)

        assert output.exists()
        data = json.loads(output.read_text())
        assert data["faithfulness"] == 0.85


class TestRAGASEvaluatorGetContexts:
    @pytest.mark.asyncio
    async def test_get_contexts_from_expected_docs(self, tmp_path):
        dataset = GoldenDataset(tmp_path / "empty.json")
        mock_llm = MagicMock()
        evaluator = RAGASEvaluator(dataset=dataset, llm_provider=mock_llm)

        contexts = await evaluator._get_contexts("test", ["doc1", "doc2"])
        assert contexts == ["doc1", "doc2"]

    @pytest.mark.asyncio
    async def test_get_contexts_from_vector_store(self, tmp_path):
        dataset = GoldenDataset(tmp_path / "empty.json")
        mock_llm = MagicMock()
        mock_store = AsyncMock()
        mock_store.search.return_value = [
            {"text": "chunk1"},
            {"text": "chunk2"},
        ]
        evaluator = RAGASEvaluator(
            dataset=dataset,
            llm_provider=mock_llm,
            vector_store=mock_store,
        )

        with patch("kb_server.embed_client.get_embedding") as mock_embed:
            mock_embed.return_value = [0.1] * 384
            contexts = await evaluator._get_contexts("test", [])

        assert contexts == ["chunk1", "chunk2"]
