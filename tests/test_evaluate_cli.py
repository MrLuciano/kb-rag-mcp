"""Tests for `kb-rag evaluate` CLI command."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from ingest.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def golden_json(tmp_path: Path) -> Path:
    path = tmp_path / "golden.json"
    path.write_text(json.dumps([
        {
            "query": "How to install?",
            "expected_answer": "Run the installer.",
            "expected_docs": ["doc1.pdf"],
        }
    ]))
    return path


@pytest.fixture
def golden_csv(tmp_path: Path) -> Path:
    path = tmp_path / "golden.csv"
    path.write_text(
        "query,expected_answer,expected_docs\n"
        "How to install?,Run the installer.,doc1.pdf\n"
    )
    return path


class TestEvaluateHelp:
    def test_help_shows_all_flags(self, runner):
        result = runner.invoke(cli, ["evaluate", "--help"])
        assert result.exit_code == 0
        assert "--dataset" in result.output
        assert "--output" in result.output
        assert "--format" in result.output
        assert "--backend" in result.output
        assert "--model" in result.output


class TestEvaluateMissingDataset:
    def test_missing_dataset_fails(self, runner):
        result = runner.invoke(cli, ["evaluate"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "--dataset" in result.output

    def test_nonexistent_dataset_fails(self, runner):
        result = runner.invoke(cli, ["evaluate", "--dataset", "/nonexistent.json"])
        assert result.exit_code != 0


class TestEvaluateJSON:
    def test_evaluate_json_dataset(self, runner, golden_json):
        with patch("kb_server.evaluation.ragas_pipeline.RAGASEvaluator.evaluate") as mock_eval:
            mock_eval.return_value = {
                "faithfulness": 0.85,
                "answer_relevancy": 0.92,
                "context_precision": 0.78,
                "context_recall": 0.88,
            }
            result = runner.invoke(cli, [
                "evaluate",
                "--dataset", str(golden_json),
                "--format", "csv",
            ])
        assert result.exit_code == 0
        assert "Faithfulness" in result.output
        assert "0.8500" in result.output

    def test_evaluate_with_output_path(self, runner, golden_json, tmp_path):
        output = tmp_path / "results.csv"
        with patch("kb_server.evaluation.ragas_pipeline.RAGASEvaluator.evaluate") as mock_eval:
            mock_eval.return_value = {"faithfulness": 0.9}
            result = runner.invoke(cli, [
                "evaluate",
                "--dataset", str(golden_json),
                "--output", str(output),
                "--format", "csv",
            ])
        assert result.exit_code == 0
        assert output.exists()
        assert "faithfulness" in output.read_text()

    def test_evaluate_json_format(self, runner, golden_json, tmp_path):
        output = tmp_path / "results.json"
        with patch("kb_server.evaluation.ragas_pipeline.RAGASEvaluator.evaluate") as mock_eval:
            mock_eval.return_value = {"faithfulness": 0.9}
            result = runner.invoke(cli, [
                "evaluate",
                "--dataset", str(golden_json),
                "--output", str(output),
                "--format", "json",
            ])
        assert result.exit_code == 0
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["summary"]["metrics"]["faithfulness"] == 0.9


class TestEvaluateCSV:
    def test_evaluate_csv_dataset(self, runner, golden_csv):
        with patch("kb_server.evaluation.ragas_pipeline.RAGASEvaluator.evaluate") as mock_eval:
            mock_eval.return_value = {
                "faithfulness": 0.85,
                "answer_relevancy": 0.92,
                "context_precision": 0.78,
                "context_recall": 0.88,
            }
            result = runner.invoke(cli, [
                "evaluate",
                "--dataset", str(golden_csv),
                "--format", "csv",
            ])
        assert result.exit_code == 0
        assert "Faithfulness" in result.output


class TestEvaluateBackend:
    def test_custom_backend(self, runner, golden_json):
        with patch("kb_server.evaluation.ragas_pipeline.RAGASEvaluator.evaluate") as mock_eval, \
                patch("ingest.cli.evaluate.os.getenv", return_value="openai-compat"):
            mock_eval.return_value = {"faithfulness": 0.9}
            result = runner.invoke(cli, [
                "evaluate",
                "--dataset", str(golden_json),
                "--backend", "ollama",
            ])
        assert result.exit_code == 0
        assert "ollama" in result.output


class TestEvaluateEmptyDataset:
    def test_empty_dataset_aborts(self, runner, tmp_path):
        empty = tmp_path / "empty.json"
        empty.write_text("[]")
        result = runner.invoke(cli, [
            "evaluate",
            "--dataset", str(empty),
        ])
        assert result.exit_code != 0
        assert "empty" in result.output.lower()


class TestEvaluateValidationWarnings:
    def test_validation_warnings_displayed(self, runner, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps([
            {"query": "", "expected_answer": "", "expected_docs": []},
        ]))
        with patch("kb_server.evaluation.ragas_pipeline.RAGASEvaluator.evaluate") as mock_eval:
            mock_eval.return_value = {"faithfulness": 0.5}
            result = runner.invoke(cli, [
                "evaluate",
                "--dataset", str(bad),
            ])
        assert result.exit_code == 0
        assert "WARNING" in result.output
