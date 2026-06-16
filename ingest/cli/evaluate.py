"""Evaluate CLI subcommand: `kb-rag evaluate`."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

import click

from kb_server.evaluation.dataset import GoldenDataset
from kb_server.evaluation.exporter import ResultsExporter
from kb_server.evaluation.ragas_pipeline import RAGASEvaluator

log = logging.getLogger("kb-rag")


def _default_output_path() -> Path:
    """Generate default output path with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(f"data/evaluation_results_{timestamp}.csv")


@click.command()
@click.option(
    "--dataset",
    "-d",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to golden dataset file (.json or .csv)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help=(
        "Output file path "
        "(default: data/evaluation_results_YYYYMMDD_HHMMSS.csv)"
    ),
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "json"], case_sensitive=False),
    default="csv",
    help="Output format (default: csv)",
)
@click.option(
    "--backend",
    "-b",
    type=str,
    default=None,
    help="Override EMBED_BACKEND for evaluation",
)
@click.option(
    "--model",
    "-m",
    type=str,
    default=None,
    help="LLM model name for judge",
)
def evaluate(
    dataset: Path,
    output: Path | None,
    format: str,
    backend: str | None,
    model: str | None,
) -> None:
    """Run RAG evaluation against a golden dataset.

    Example:
        kb-rag evaluate --dataset data/golden.json
        kb-rag evaluate --dataset data/golden.csv \
            --output results.csv --format csv
    """
    # Resolve backend
    eval_backend = backend or os.getenv("EMBED_BACKEND", "lmstudio-rest")
    eval_model = model or os.getenv("EVAL_LLM_MODEL", "default")

    click.echo(f"Evaluating with backend: {eval_backend}")
    if eval_model != "default":
        click.echo(f"Judge model: {eval_model}")

    # Load dataset
    try:
        golden_dataset = GoldenDataset(dataset)
    except ValueError as e:
        raise click.BadParameter(str(e))

    if not golden_dataset.examples:
        click.echo("ERROR: Dataset is empty or could not be loaded.", err=True)
        raise click.Abort()

    click.echo(f"Loaded {len(golden_dataset)} examples from {dataset}")

    # Validate dataset
    errors = golden_dataset.validate()
    if errors:
        click.echo("WARNING: Dataset validation issues:", err=True)
        for err in errors[:10]:  # Show first 10
            click.echo(f"  - {err}", err=True)
        if len(errors) > 10:
            click.echo(f"  ... and {len(errors) - 10} more", err=True)

    # Run evaluation
    assert eval_backend is not None
    assert eval_model is not None
    evaluator = RAGASEvaluator(
        dataset=golden_dataset,
        backend=eval_backend,
        model=eval_model,
    )

    try:
        results = asyncio.run(evaluator.evaluate())
    except Exception as e:
        log.error("Evaluation failed: %s", e)
        click.echo(f"ERROR: Evaluation failed: {e}", err=True)
        raise click.Abort()

    # Display results
    click.echo()
    console_output = ResultsExporter.to_console(results)
    click.echo(console_output)

    # Export results
    if output is None:
        output = _default_output_path()
        output.parent.mkdir(parents=True, exist_ok=True)

    # Add correct extension if missing
    if not output.suffix:
        output = output.with_suffix(f".{format.lower()}")

    if format.lower() == "csv":
        ResultsExporter.to_csv(results, output)
    elif format.lower() == "json":
        ResultsExporter.to_json(results, output)
    else:
        raise click.BadParameter(f"Unsupported format: {format}")

    click.echo(f"\nResults exported to: {output}")
