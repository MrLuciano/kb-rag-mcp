"""Optimize CLI subcommand: `kb-rag optimize`."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict

import click

from kb_server.evaluation.dataset import GoldenDataset
from kb_server.evaluation.exporter import ResultsExporter
from kb_server.optimization.experiment_runner import ExperimentRunner
from kb_server.vector_store import VectorStore

log = logging.getLogger("kb-rag")


def _backend_default() -> str:
    """Return the default embedding backend from env."""
    return os.getenv("EMBED_BACKEND", "lmstudio-rest")


def _collection_default() -> str:
    """Return the default Qdrant collection from env."""
    return os.getenv("QDRANT_COLLECTION", "kb_docs")


@click.group()
def optimize() -> None:
    """Run optimization experiments for chunking and scoring strategies."""


@optimize.command()
@click.option(
    "--dataset",
    "-d",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to golden dataset file (.json or .csv)",
)
@click.option(
    "--docs",
    "-D",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Documents directory path",
)
@click.option(
    "--strategy",
    "-s",
    type=click.Choice(["fixed", "recursive", "semantic"]),
    required=True,
    help="Chunking strategy",
)
@click.option(
    "--chunk-size",
    "-c",
    type=int,
    default=None,
    help="Chunk size override",
)
@click.option(
    "--overlap",
    "-o",
    type=int,
    default=None,
    help="Chunk overlap override",
)
@click.option(
    "--top-k",
    "-k",
    type=int,
    default=5,
    help="Number of top results to evaluate",
)
@click.option(
    "--output",
    "-O",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output file path (CSV or JSON)",
)
@click.option(
    "--backend",
    "-b",
    type=str,
    default=None,
    help="Override EMBED_BACKEND",
)
@click.option(
    "--collection",
    type=str,
    default=None,
    help="Qdrant collection name (default: QDRANT_COLLECTION env var)",
)
def chunk(
    dataset: Path,
    docs: Path,
    strategy: str,
    chunk_size: int | None,
    overlap: int | None,
    top_k: int,
    output: Path | None,
    backend: str | None,
    collection: str | None,
) -> None:
    """Run a chunking optimization experiment.

    Example:
        kb-rag optimize chunk --dataset data/golden.json \\
            --docs data/docs --strategy fixed --chunk-size 512
    """
    # Resolve backend and collection
    eval_backend = backend or _backend_default()
    eval_collection = collection or _collection_default()

    click.echo(f"Backend: {eval_backend}")
    click.echo(f"Collection: {eval_collection}")

    # Load dataset
    try:
        golden_dataset = GoldenDataset(dataset)
    except ValueError as e:
        raise click.BadParameter(str(e))

    if not golden_dataset.examples:
        click.echo("ERROR: Dataset is empty.", err=True)
        raise click.Abort()

    click.echo(f"Loaded {len(golden_dataset)} examples from {dataset}")

    errors = golden_dataset.validate()
    if errors:
        click.echo("WARNING: Dataset validation issues:", err=True)
        for err in errors[:10]:
            click.echo(f"  - {err}", err=True)

    # Init vector store
    store = VectorStore()
    store.collection = eval_collection

    try:
        asyncio.run(store.connect())
    except Exception as e:
        click.echo(
            f"WARNING: Could not connect to Qdrant: {e}", err=True
        )

    # Create runner and run experiment
    runner = ExperimentRunner(store, golden_dataset)

    try:
        result = asyncio.run(
            runner.run_chunking_experiment(
                docs_path=docs,
                strategy=strategy,
                chunk_size=chunk_size,
                overlap=overlap,
                top_k=top_k,
            )
        )
    except Exception as e:
        log.error("Chunking experiment failed: %s", e)
        click.echo(f"ERROR: Experiment failed: {e}", err=True)
        raise click.Abort()

    # Display results
    click.echo()
    console_output = ResultsExporter.to_console(result["metrics"])
    click.echo(console_output)

    # Export if requested
    if output is not None:
        if output.suffix.lower() == ".csv":
            ResultsExporter.to_csv(result["metrics"], output)
        elif output.suffix.lower() == ".json":
            ResultsExporter.to_json(result["metrics"], output)
        else:
            click.echo(
                "WARNING: Unknown output format; defaulting to JSON",
                err=True,
            )
            ResultsExporter.to_json(result["metrics"], output)
        click.echo(f"\nResults exported to: {output}")


@optimize.command()
@click.option(
    "--dataset",
    "-d",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to golden dataset file (.json or .csv)",
)
@click.option(
    "--variant",
    "-v",
    type=click.Choice(["dense_only", "hybrid", "reranked"]),
    required=True,
    help="Scoring variant",
)
@click.option(
    "--top-k",
    "-k",
    type=int,
    default=5,
    help="Number of top results to evaluate",
)
@click.option(
    "--output",
    "-O",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output file path (CSV or JSON)",
)
@click.option(
    "--backend",
    "-b",
    type=str,
    default=None,
    help="Override EMBED_BACKEND",
)
@click.option(
    "--collection",
    type=str,
    default=None,
    help="Qdrant collection name (default: QDRANT_COLLECTION env var)",
)
@click.option(
    "--distance-metric",
    type=str,
    default=None,
    help="For dense_only: COSINE, DOT, EUCLID, MANHATTAN",
)
@click.option(
    "--dense-weight",
    type=float,
    default=None,
    help="For hybrid: 0.0-1.0",
)
@click.option(
    "--sparse-weight",
    type=float,
    default=None,
    help="For hybrid: 0.0-1.0",
)
def scoring(
    dataset: Path,
    variant: str,
    top_k: int,
    output: Path | None,
    backend: str | None,
    collection: str | None,
    distance_metric: str | None,
    dense_weight: float | None,
    sparse_weight: float | None,
) -> None:
    """Run a scoring optimization experiment.

    Example:
        kb-rag optimize scoring --dataset data/golden.json \\
            --variant hybrid --dense-weight 0.8 --sparse-weight 0.2
    """
    eval_backend = backend or _backend_default()
    eval_collection = collection or _collection_default()

    click.echo(f"Backend: {eval_backend}")
    click.echo(f"Collection: {eval_collection}")

    # Load dataset
    try:
        golden_dataset = GoldenDataset(dataset)
    except ValueError as e:
        raise click.BadParameter(str(e))

    if not golden_dataset.examples:
        click.echo("ERROR: Dataset is empty.", err=True)
        raise click.Abort()

    click.echo(f"Loaded {len(golden_dataset)} examples from {dataset}")

    errors = golden_dataset.validate()
    if errors:
        click.echo("WARNING: Dataset validation issues:", err=True)
        for err in errors[:10]:
            click.echo(f"  - {err}", err=True)

    # Init vector store
    store = VectorStore()
    store.collection = eval_collection

    try:
        asyncio.run(store.connect())
    except Exception as e:
        click.echo(
            f"WARNING: Could not connect to Qdrant: {e}", err=True
        )

    # Build variant kwargs
    variant_kwargs: Dict[str, Any] = {}
    if distance_metric is not None:
        variant_kwargs["distance_metric"] = distance_metric
    if dense_weight is not None:
        variant_kwargs["dense_weight"] = dense_weight
    if sparse_weight is not None:
        variant_kwargs["sparse_weight"] = sparse_weight

    # Create runner and run experiment
    runner = ExperimentRunner(store, golden_dataset)

    try:
        result = asyncio.run(
            runner.run_scoring_experiment(
                variant=variant,
                top_k=top_k,
                **variant_kwargs,
            )
        )
    except Exception as e:
        log.error("Scoring experiment failed: %s", e)
        click.echo(f"ERROR: Experiment failed: {e}", err=True)
        raise click.Abort()

    # Display results
    click.echo()
    console_output = ResultsExporter.to_console(result["metrics"])
    click.echo(console_output)

    # Export if requested
    if output is not None:
        if output.suffix.lower() == ".csv":
            ResultsExporter.to_csv(result["metrics"], output)
        elif output.suffix.lower() == ".json":
            ResultsExporter.to_json(result["metrics"], output)
        else:
            click.echo(
                "WARNING: Unknown output format; defaulting to JSON",
                err=True,
            )
            ResultsExporter.to_json(result["metrics"], output)
        click.echo(f"\nResults exported to: {output}")


@optimize.command()
@click.option(
    "--run-ids",
    "-r",
    multiple=True,
    required=True,
    help="Run IDs to compare",
)
@click.option(
    "--output",
    "-O",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output file path (CSV or JSON)",
)
def compare(run_ids: tuple[str, ...], output: Path | None) -> None:
    """Compare experiment runs.

    Example:
        kb-rag optimize compare --run-ids chunk_fixed_512_20260101_120000 \\
            --run-ids score_hybrid_20260101_120000
    """
    from kb_server.optimization.result_store import ExperimentResultStore

    store = ExperimentResultStore()
    comparison = store.compare(list(run_ids))

    if not comparison.get("runs"):
        click.echo("No runs found for comparison.", err=True)
        raise click.Abort()

    # Display comparison table
    click.echo()
    click.echo("Comparison Results")
    click.echo("=" * 50)

    for run in comparison["runs"]:
        click.echo(f"\nRun: {run.get('run_id', 'unknown')}")
        metrics = run.get("metrics", {})
        for key, value in metrics.items():
            click.echo(f"  {key}: {value}")

    # Show deltas
    deltas = comparison.get("deltas", {})
    if deltas:
        click.echo("\nDeltas:")
        for metric_name, values in deltas.items():
            click.echo(f"  {metric_name}:")
            for run_id, val in values:
                click.echo(f"    {run_id}: {val}")

    # Export if requested
    if output is not None:
        if output.suffix.lower() == ".csv":
            ResultsExporter.to_csv(
                {"comparison": comparison["deltas"]}, output
            )
        elif output.suffix.lower() == ".json":
            ResultsExporter.to_json(
                {"comparison": comparison["deltas"]}, output
            )
        else:
            ResultsExporter.to_json(
                {"comparison": comparison["deltas"]}, output
            )
        click.echo(f"\nComparison exported to: {output}")


@optimize.command(name="list")
def list_runs() -> None:
    """List all saved experiment runs."""
    from kb_server.optimization.result_store import ExperimentResultStore

    store = ExperimentResultStore()
    runs = store.list_runs()

    if not runs:
        click.echo("No experiment runs found.")
        return

    click.echo(f"Found {len(runs)} experiment runs:\n")
    for run in runs:
        click.echo(
            f"  {run.get('run_id', 'unknown')}  "
            f"({run.get('strategy', '')} / {run.get('variant', '')})  "
            f"{run.get('timestamp', '')}"
        )
