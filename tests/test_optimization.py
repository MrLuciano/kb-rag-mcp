"""Integration tests for optimization experiment runner and CLI.

FASE 25: Optimization Experiments
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from kb_server.optimization.experiment_runner import (
    ExperimentRunner,
    run_chunking_experiment,
    run_scoring_experiment,
)
from ingest.cli.optimize import optimize

pytestmark = pytest.mark.fase25


# ── ExperimentRunner tests ───────────────────────────────────────────


class TestExperimentRunner:
    def test_experiment_runner_init(self):
        """Runner creates store and stores references."""
        mock_store = MagicMock()
        mock_dataset = MagicMock()
        runner = ExperimentRunner(mock_store, mock_dataset)
        assert runner.vector_store is mock_store
        assert runner.dataset is mock_dataset
        assert runner.store is not None

    @pytest.mark.asyncio
    async def test_run_chunking_experiment(self):
        """Mock ChunkingEngine, verify result dict with run_id and metrics."""
        mock_store = MagicMock()
        mock_store.collection = "kb_docs"
        mock_dataset = MagicMock()
        mock_dataset.examples = []

        runner = ExperimentRunner(mock_store, mock_dataset)

        with patch(
            "kb_server.optimization.experiment_runner.ChunkingEngine"
        ) as mock_engine_cls:
            mock_engine = AsyncMock()
            mock_engine.run_experiment.return_value = {
                "recall_at_k": 0.75,
                "mrr": 0.5,
                "ndcg_at_k": 0.6,
                "chunk_count": 10,
                "strategy_name": "FixedStrategy",
            }
            mock_engine_cls.return_value = mock_engine

            result = await runner.run_chunking_experiment(
                docs_path=Path("/tmp/docs"),
                strategy="fixed",
                chunk_size=256,
                top_k=5,
                run_id="test_chunk_run",
            )

        assert result["run_id"] == "test_chunk_run"
        assert "metrics" in result
        assert result["metrics"]["recall_at_k"] == 0.75
        assert "output_path" in result

    @pytest.mark.asyncio
    async def test_run_scoring_experiment(self):
        """Mock ScoringEngine, verify result dict with run_id and metrics."""
        mock_store = MagicMock()
        mock_dataset = MagicMock()
        mock_dataset.examples = []

        runner = ExperimentRunner(mock_store, mock_dataset)

        with patch(
            "kb_server.optimization.experiment_runner.ScoringEngine"
        ) as mock_engine_cls:
            mock_engine = AsyncMock()
            mock_engine.run_experiment.return_value = {
                "recall_at_k": 0.8,
                "mrr": 0.6,
                "ndcg_at_k": 0.7,
                "variant_name": "DenseOnlyVariant",
            }
            mock_engine_cls.return_value = mock_engine

            result = await runner.run_scoring_experiment(
                variant="dense_only",
                top_k=5,
                run_id="test_score_run",
            )

        assert result["run_id"] == "test_score_run"
        assert "metrics" in result
        assert result["metrics"]["recall_at_k"] == 0.8
        assert "output_path" in result

    @pytest.mark.asyncio
    async def test_run_parameter_sweep_chunking(self):
        """2 strategies x 2 chunk_sizes = 4 combinations."""
        mock_store = MagicMock()
        mock_dataset = MagicMock()
        runner = ExperimentRunner(mock_store, mock_dataset)

        with patch.object(
            runner, "run_chunking_experiment", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = {
                "run_id": "test",
                "metrics": {"recall_at_k": 0.5},
                "output_path": "/tmp/test.json",
            }

            results = await runner.run_parameter_sweep(
                experiment_type="chunking",
                param_grid={
                    "strategy": ["fixed", "recursive"],
                    "chunk_size": [256, 512],
                },
                docs_path=Path("/tmp/docs"),
            )

        assert len(results) == 4
        assert mock_run.await_count == 4

    @pytest.mark.asyncio
    async def test_run_parameter_sweep_scoring(self):
        """2 variants = 2 combinations."""
        mock_store = MagicMock()
        mock_dataset = MagicMock()
        runner = ExperimentRunner(mock_store, mock_dataset)

        with patch.object(
            runner, "run_scoring_experiment", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = {
                "run_id": "test",
                "metrics": {"recall_at_k": 0.5},
                "output_path": "/tmp/test.json",
            }

            results = await runner.run_parameter_sweep(
                experiment_type="scoring",
                param_grid={
                    "variant": ["dense_only", "hybrid"],
                },
            )

        assert len(results) == 2
        assert mock_run.await_count == 2

    @pytest.mark.asyncio
    async def test_compare_runs(self):
        """Save 2 mock runs, compare them, verify deltas present."""
        mock_store = MagicMock()
        mock_dataset = MagicMock()
        runner = ExperimentRunner(mock_store, mock_dataset)

        with patch.object(runner.store, "compare") as mock_compare:
            mock_compare.return_value = {
                "runs": [
                    {
                        "run_id": "run_a",
                        "metrics": {"recall_at_k": 0.6},
                    },
                    {
                        "run_id": "run_b",
                        "metrics": {"recall_at_k": 0.8},
                    },
                ],
                "deltas": {
                    "recall_at_k": [
                        ("run_a", 0.6),
                        ("run_b", 0.8),
                    ]
                },
            }

            result = await runner.compare_runs(["run_a", "run_b"])

        assert "runs" in result
        assert "deltas" in result
        assert "table" in result
        assert len(result["runs"]) == 2

    @pytest.mark.asyncio
    async def test_list_runs(self):
        """Save 2 runs via store, list them, verify 2 returned."""
        mock_store = MagicMock()
        mock_dataset = MagicMock()
        runner = ExperimentRunner(mock_store, mock_dataset)

        with patch.object(
            runner.store, "list_runs"
        ) as mock_list:
            mock_list.return_value = [
                {"run_id": "run_1", "strategy": "fixed"},
                {"run_id": "run_2", "strategy": "hybrid"},
            ]

            runs = await runner.list_runs()

        assert len(runs) == 2

    @pytest.mark.asyncio
    async def test_compare_runs_empty(self):
        """compare with no run_ids returns empty dict."""
        mock_store = MagicMock()
        mock_dataset = MagicMock()
        runner = ExperimentRunner(mock_store, mock_dataset)

        result = await runner.compare_runs([])
        assert result == {"runs": [], "deltas": {}, "table": ""}


# ── Standalone convenience functions ───────────────────────────────


class TestStandaloneFunctions:
    @pytest.mark.asyncio
    async def test_run_chunking_experiment_standalone(self):
        """Convenience wrapper creates runner and returns result."""
        mock_store = MagicMock()
        mock_dataset = MagicMock()

        with patch(
            "kb_server.optimization.experiment_runner.ExperimentRunner"
        ) as mock_runner_cls:
            mock_runner = AsyncMock()
            mock_runner.run_chunking_experiment.return_value = {
                "run_id": "standalone_chunk",
                "metrics": {},
                "output_path": "/tmp/out.json",
            }
            mock_runner_cls.return_value = mock_runner

            result = await run_chunking_experiment(
                vector_store=mock_store,
                dataset=mock_dataset,
                docs_path=Path("/tmp/docs"),
                strategy="fixed",
            )

        assert result["run_id"] == "standalone_chunk"

    @pytest.mark.asyncio
    async def test_run_scoring_experiment_standalone(self):
        """Convenience wrapper creates runner and returns result."""
        mock_store = MagicMock()
        mock_dataset = MagicMock()

        with patch(
            "kb_server.optimization.experiment_runner.ExperimentRunner"
        ) as mock_runner_cls:
            mock_runner = AsyncMock()
            mock_runner.run_scoring_experiment.return_value = {
                "run_id": "standalone_score",
                "metrics": {},
                "output_path": "/tmp/out.json",
            }
            mock_runner_cls.return_value = mock_runner

            result = await run_scoring_experiment(
                vector_store=mock_store,
                dataset=mock_dataset,
                variant="dense_only",
            )

        assert result["run_id"] == "standalone_score"


# ── CLI tests ───────────────────────────────────────────────────────


class TestOptimizeCLI:
    def test_optimize_cli_group_exists(self):
        """optimize import succeeds and is a click.Group."""
        import click

        assert isinstance(optimize, click.Group)

    def test_optimize_chunk_command(self, tmp_path):
        """Mock runner and dataset, invoke chunk subcommand."""
        dataset_file = tmp_path / "golden.json"
        dataset_file.write_text("[]")
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        runner = CliRunner()

        with patch(
            "ingest.cli.optimize.ExperimentRunner"
        ) as mock_runner_cls:
            mock_runner = AsyncMock()
            mock_runner.run_chunking_experiment.return_value = {
                "run_id": "cli_chunk",
                "metrics": {
                    "recall_at_k": 0.5,
                    "mrr": 0.5,
                    "ndcg_at_k": 0.5,
                },
                "output_path": "/tmp/out.json",
            }
            mock_runner_cls.return_value = mock_runner

            with patch(
                "ingest.cli.optimize.VectorStore"
            ) as mock_vs_cls:
                mock_vs = MagicMock()
                mock_vs_cls.return_value = mock_vs

                with patch(
                    "ingest.cli.optimize.GoldenDataset"
                ) as mock_ds_cls:
                    mock_ds = MagicMock()
                    mock_ds.examples = [{"query": "q"}]
                    mock_ds.validate.return_value = []
                    mock_ds_cls.return_value = mock_ds

                    result = runner.invoke(
                        optimize,
                        [
                            "chunk",
                            "--dataset",
                            str(dataset_file),
                            "--docs",
                            str(docs_dir),
                            "--strategy",
                            "fixed",
                        ],
                    )

        assert result.exit_code == 0

    def test_optimize_scoring_command(self, tmp_path):
        """Mock runner and dataset, invoke scoring subcommand."""
        dataset_file = tmp_path / "golden.json"
        dataset_file.write_text("[]")

        runner = CliRunner()

        with patch(
            "ingest.cli.optimize.ExperimentRunner"
        ) as mock_runner_cls:
            mock_runner = AsyncMock()
            mock_runner.run_scoring_experiment.return_value = {
                "run_id": "cli_score",
                "metrics": {
                    "recall_at_k": 0.5,
                    "mrr": 0.5,
                    "ndcg_at_k": 0.5,
                },
                "output_path": "/tmp/out.json",
            }
            mock_runner_cls.return_value = mock_runner

            with patch(
                "ingest.cli.optimize.VectorStore"
            ) as mock_vs_cls:
                mock_vs = MagicMock()
                mock_vs_cls.return_value = mock_vs

                with patch(
                    "ingest.cli.optimize.GoldenDataset"
                ) as mock_ds_cls:
                    mock_ds = MagicMock()
                    mock_ds.examples = [{"query": "q"}]
                    mock_ds.validate.return_value = []
                    mock_ds_cls.return_value = mock_ds

                    result = runner.invoke(
                        optimize,
                        [
                            "scoring",
                            "--dataset",
                            str(dataset_file),
                            "--variant",
                            "dense_only",
                        ],
                    )

        assert result.exit_code == 0

    def test_optimize_compare_command(self):
        """Mock result store, invoke compare subcommand."""
        runner = CliRunner()

        with patch(
            "kb_server.optimization.result_store.ExperimentResultStore"
        ) as mock_store_cls:
            mock_store = MagicMock()
            mock_store.compare.return_value = {
                "runs": [
                    {"run_id": "r1", "metrics": {"recall_at_k": 0.5}}
                ],
                "deltas": {"recall_at_k": [("r1", 0.5)]},
            }
            mock_store_cls.return_value = mock_store

            result = runner.invoke(
                optimize,
                [
                    "compare",
                    "--run-ids",
                    "r1",
                ],
            )

        assert result.exit_code == 0

    def test_optimize_list_command(self):
        """Invoke list subcommand, verify exit code 0."""
        runner = CliRunner()

        with patch(
            "kb_server.optimization.result_store.ExperimentResultStore"
        ) as mock_store_cls:
            mock_store = MagicMock()
            mock_store.list_runs.return_value = [
                {"run_id": "r1", "strategy": "fixed"}
            ]
            mock_store_cls.return_value = mock_store

            result = runner.invoke(
                optimize,
                ["list"],
            )

        assert result.exit_code == 0
        assert "r1" in result.output
