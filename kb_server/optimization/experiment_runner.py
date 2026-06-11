"""Experiment orchestration and parameter sweep for optimization.

FASE 25: Optimization Experiments

Provides :class:`ExperimentRunner` which ties chunking experiments,
scoring experiments, and result comparison into a single user-facing
workflow.
"""

import itertools
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from kb_server.evaluation.dataset import GoldenDataset
from kb_server.evaluation.exporter import ResultsExporter
from kb_server.optimization.chunking_experiments import (
    ChunkingEngine,
    create_strategy,
)
from kb_server.optimization.result_store import ExperimentResultStore
from kb_server.optimization.scoring_experiments import (
    ScoringEngine,
    create_variant,
)

log = logging.getLogger("kb-mcp.optimization")


class ExperimentRunner:
    """Orchestrate chunking and scoring experiments with result storage.

    The runner wraps :class:`ChunkingEngine` and :class:`ScoringEngine`,
    persists results via :class:`ExperimentResultStore`, and supports
    parameter sweeps and cross-run comparison.
    """

    def __init__(
        self,
        vector_store: Any,
        dataset: GoldenDataset,
        output_dir: Path = Path("data/experiments"),
    ) -> None:
        """Initialise runner.

        Args:
            vector_store: Connected ``VectorStore`` instance.
            dataset: Loaded golden dataset.
            output_dir: Directory for experiment JSON files.
        """
        self.vector_store = vector_store
        self.dataset = dataset
        self.store = ExperimentResultStore(output_dir)

    async def run_chunking_experiment(
        self,
        docs_path: Path,
        strategy: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        top_k: int = 5,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run a single chunking experiment and save results.

        Args:
            docs_path: Directory containing documents to ingest.
            strategy: Chunking strategy name (``fixed``, ``recursive``,
                ``semantic``).
            chunk_size: Optional chunk size override.
            overlap: Optional chunk overlap override.
            top_k: Number of top results to evaluate.
            run_id: Optional run identifier.  Auto-generated if omitted.

        Returns:
            Result dict with ``run_id``, ``metrics``, ``output_path``.
        """
        if run_id is None:
            run_id = (
                f"chunk_{strategy}_{chunk_size}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

        log.info(
            "Running chunking experiment: %s (strategy=%s, size=%s, "
            "overlap=%s)",
            run_id,
            strategy,
            chunk_size,
            overlap,
        )

        strategy_obj = create_strategy(
            strategy,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        engine = ChunkingEngine(
            strategy_obj, self.vector_store, self.dataset
        )
        metrics = await engine.run_experiment(
            docs_path, top_k=top_k, clean=True
        )

        params = {
            "strategy": strategy,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "top_k": top_k,
        }
        output_path = self.store.save(
            run_id=run_id,
            params=params,
            metrics=metrics,
            strategy=strategy,
            variant="chunking",
        )

        log.info("Chunking experiment complete: %s -> %s", run_id, output_path)
        return {
            "run_id": run_id,
            "metrics": metrics,
            "output_path": str(output_path),
        }

    async def run_scoring_experiment(
        self,
        variant: str,
        top_k: int = 5,
        run_id: Optional[str] = None,
        **variant_kwargs: Any,
    ) -> Dict[str, Any]:
        """Run a single scoring experiment and save results.

        Args:
            variant: Scoring variant name (``dense_only``, ``hybrid``,
                ``reranked``).
            top_k: Number of top results to evaluate.
            run_id: Optional run identifier.  Auto-generated if omitted.
            **variant_kwargs: Extra arguments passed to ``create_variant``.

        Returns:
            Result dict with ``run_id``, ``metrics``, ``output_path``.
        """
        if run_id is None:
            run_id = (
                f"score_{variant}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

        log.info(
            "Running scoring experiment: %s (variant=%s, top_k=%d)",
            run_id,
            variant,
            top_k,
        )

        variant_obj = create_variant(variant, **variant_kwargs)
        engine = ScoringEngine(variant_obj, self.vector_store, self.dataset)
        metrics = await engine.run_experiment(top_k=top_k)

        params = {"variant": variant, "top_k": top_k, **variant_kwargs}
        output_path = self.store.save(
            run_id=run_id,
            params=params,
            metrics=metrics,
            strategy=variant,
            variant="scoring",
        )

        log.info("Scoring experiment complete: %s -> %s", run_id, output_path)
        return {
            "run_id": run_id,
            "metrics": metrics,
            "output_path": str(output_path),
        }

    async def run_parameter_sweep(
        self,
        experiment_type: str,
        param_grid: Dict[str, List[Any]],
        docs_path: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        """Run a parameter sweep over all combinations.

        Args:
            experiment_type: ``chunking`` or ``scoring``.
            param_grid: Dict mapping parameter names to lists of values.
            docs_path: Required for chunking experiments.

        Returns:
            List of result dicts, one per combination.
        """
        if experiment_type not in ("chunking", "scoring"):
            raise ValueError(
                f"experiment_type must be 'chunking' or 'scoring', "
                f"got '{experiment_type}'"
            )

        keys = list(param_grid.keys())
        values = [param_grid[k] for k in keys]
        combinations = list(itertools.product(*values))

        log.info(
            "Parameter sweep: %d combinations for %s",
            len(combinations),
            experiment_type,
        )

        results: List[Dict[str, Any]] = []
        baseline_saved = False

        for i, combo in enumerate(combinations):
            params = dict(zip(keys, combo))
            run_id = (
                f"sweep_{experiment_type}_{i}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

            if experiment_type == "chunking":
                if docs_path is None:
                    raise ValueError(
                        "docs_path is required for chunking sweep"
                    )
                result = await self.run_chunking_experiment(
                    docs_path=docs_path,
                    run_id=run_id,
                    **params,
                )
            else:
                result = await self.run_scoring_experiment(
                    run_id=run_id,
                    **params,
                )

            results.append(result)

            # Auto-save baseline for the first run if none exists yet
            if not baseline_saved and not self.store.baseline():
                self.store.save(
                    run_id="baseline",
                    params=result.get("metrics", {}),
                    metrics=result.get("metrics", {}),
                    strategy=params.get(
                        "strategy", params.get("variant", "")
                    ),
                    variant=experiment_type,
                )
                baseline_saved = True
                log.info("Auto-saved baseline run")

        log.info("Parameter sweep complete: %d results", len(results))
        return results

    async def compare_runs(self, run_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple experiment runs.

        Args:
            run_ids: List of run identifiers to compare.

        Returns:
            Comparison dict with ``runs``, ``deltas``, and ``table``.
        """
        if not run_ids:
            return {"runs": [], "deltas": {}, "table": ""}

        comparison = self.store.compare(run_ids)

        # Build a formatted console table
        table_data: Dict[str, float] = {}
        for run in comparison.get("runs", []):
            metrics = run.get("metrics", {})
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    table_data[f"{run['run_id']}_{key}"] = value

        table_str = ResultsExporter.to_console(table_data)
        comparison["table"] = table_str
        return comparison

    async def list_runs(self) -> List[Dict[str, Any]]:
        """List all saved experiment runs.

        Returns:
            List of run metadata dicts.
        """
        return self.store.list_runs()


# ── Standalone convenience functions ─────────────────────────────────


async def run_chunking_experiment(
    vector_store: Any,
    dataset: GoldenDataset,
    docs_path: Path,
    strategy: str,
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None,
    top_k: int = 5,
    run_id: Optional[str] = None,
    output_dir: Path = Path("data/experiments"),
) -> Dict[str, Any]:
    """Run a single chunking experiment (convenience wrapper).

    Creates an :class:`ExperimentRunner` and delegates to
    :meth:`ExperimentRunner.run_chunking_experiment`.
    """
    runner = ExperimentRunner(vector_store, dataset, output_dir)
    return await runner.run_chunking_experiment(
        docs_path=docs_path,
        strategy=strategy,
        chunk_size=chunk_size,
        overlap=overlap,
        top_k=top_k,
        run_id=run_id,
    )


async def run_scoring_experiment(
    vector_store: Any,
    dataset: GoldenDataset,
    variant: str,
    top_k: int = 5,
    run_id: Optional[str] = None,
    output_dir: Path = Path("data/experiments"),
    **variant_kwargs: Any,
) -> Dict[str, Any]:
    """Run a single scoring experiment (convenience wrapper).

    Creates an :class:`ExperimentRunner` and delegates to
    :meth:`ExperimentRunner.run_scoring_experiment`.
    """
    runner = ExperimentRunner(vector_store, dataset, output_dir)
    return await runner.run_scoring_experiment(
        variant=variant,
        top_k=top_k,
        run_id=run_id,
        **variant_kwargs,
    )
