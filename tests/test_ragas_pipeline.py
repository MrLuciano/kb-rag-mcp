"""Tests for RAGAS evaluation pipeline."""
import json
import pytest
from pathlib import Path
from server.evaluation.ragas_pipeline import RAGASEvaluator
from server.evaluation.dataset import GoldenDataset


@pytest.fixture
def mock_dataset(tmp_path):
    """Create mock golden dataset."""
    examples = [
        {
            "query": "How to install?",
            "expected_answer": "Run install.sh",
            "expected_docs": ["guide.pdf"],
            "metadata": {},
        }
    ]
    dataset_path = tmp_path / "dataset.json"
    with open(dataset_path, "w") as f:
        json.dump(examples, f)
    return GoldenDataset(dataset_path=dataset_path)


def test_evaluator_initialization(mock_dataset):
    """Test RAGASEvaluator initialization."""
    evaluator = RAGASEvaluator(dataset=mock_dataset)
    assert evaluator.dataset == mock_dataset
    assert evaluator.llm_provider == "ollama"
    assert evaluator.model == "llama2"


def test_evaluator_custom_provider(mock_dataset):
    """Test RAGASEvaluator with custom provider."""
    evaluator = RAGASEvaluator(
        dataset=mock_dataset, llm_provider="openai", model="gpt-4"
    )
    assert evaluator.llm_provider == "openai"
    assert evaluator.model == "gpt-4"


def test_evaluate_raises_not_implemented(mock_dataset):
    """Test that evaluate raises NotImplementedError (requires LLM)."""
    evaluator = RAGASEvaluator(dataset=mock_dataset)
    with pytest.raises(NotImplementedError):
        evaluator.evaluate()


def test_save_results(mock_dataset, tmp_path):
    """Test saving evaluation results to JSON."""
    evaluator = RAGASEvaluator(dataset=mock_dataset)
    results = {
        "context_precision": 0.85,
        "context_recall": 0.72,
        "answer_relevancy": 0.91,
        "faithfulness": 0.88,
    }
    output_path = tmp_path / "results.json"
    evaluator.save_results(results, output_path)

    assert output_path.exists()
    loaded = json.loads(output_path.read_text())
    assert loaded == results


@pytest.mark.skip(reason="Requires LLM API, expensive")
def test_run_evaluation(mock_dataset):
    """Test running RAGAS evaluation."""
    evaluator = RAGASEvaluator(dataset=mock_dataset)
    results = evaluator.evaluate()
    assert "context_precision" in results
    assert "answer_relevancy" in results
    assert "faithfulness" in results
