"""Results exporter for RAG evaluation.

Supports CSV, JSON, and rich console table output.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

log = logging.getLogger("kb-mcp.eval")


class ResultsExporter:
    """Export evaluation results in multiple formats."""

    @staticmethod
    def to_csv(
        results: Dict[str, Any],
        output_path: Path,
        per_example_scores: List[Dict[str, Any]] | None = None,
    ) -> None:
        """Export results to CSV.

        Args:
            results: Dict with metric_name -> mean_score.
            output_path: Path for output CSV file.
            per_example_scores: Optional list of per-example scores.
        """
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            if per_example_scores:
                # Per-example format
                headers = ["example_index", "query"]
                if per_example_scores:
                    headers.extend(
                        k
                        for k in per_example_scores[0].keys()
                        if k not in ("example_index", "query", "timestamp")
                    )
                headers.append("timestamp")
                writer.writerow(headers)

                for i, row in enumerate(per_example_scores):
                    writer.writerow(
                        [
                            i,
                            row.get("query", ""),
                            *[row.get(k, "") for k in headers[2:-1]],
                            row.get("timestamp", ""),
                        ]
                    )
            else:
                # Summary-only format
                writer.writerow(["metric", "score", "timestamp"])
                for metric, score in results.items():
                    writer.writerow(
                        [
                            metric,
                            f"{score:.4f}",
                            datetime.now(timezone.utc)
                            .replace(tzinfo=None)
                            .isoformat()
                            + "Z",
                        ]
                    )

        log.info("Results exported to CSV: %s", output_path)

    @staticmethod
    def to_json(
        results: Dict[str, Any],
        output_path: Path,
        per_example_scores: List[Dict[str, Any]] | None = None,
    ) -> None:
        """Export results to JSON with summary statistics.

        Args:
            results: Dict with metric_name -> mean_score.
            output_path: Path for output JSON file.
            per_example_scores: Optional list of per-example scores.
        """
        data: Dict[str, Any] = {
            "summary": {
                "metrics": results,
                "timestamp": datetime.now(timezone.utc)
                .replace(tzinfo=None)
                .isoformat()
                + "Z",
            },
        }

        if per_example_scores:
            data["per_example"] = per_example_scores

            # Compute stats per metric
            stats: Dict[str, Dict[str, float]] = {}
            for metric in results.keys():
                values = [r[metric] for r in per_example_scores if metric in r]
                if values:
                    stats[metric] = {
                        "mean": round(sum(values) / len(values), 4),
                        "min": round(min(values), 4),
                        "max": round(max(values), 4),
                        "count": len(values),
                    }
            data["summary"]["stats"] = stats

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        log.info("Results exported to JSON: %s", output_path)

    @staticmethod
    def to_console(results: Dict[str, float]) -> str:
        """Format results as a console table string.

        Uses rich if available, falls back to plain text.

        Args:
            results: Dict with metric_name -> mean_score.

        Returns:
            Formatted table string.
        """
        try:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(title="RAG Evaluation Results")
            table.add_column("Metric", style="cyan", no_wrap=True)
            table.add_column("Score", justify="right", style="green")

            for metric, score in results.items():
                # Format metric name for display
                display_name = metric.replace("_", " ").title()
                table.add_row(display_name, f"{score:.4f}")

            # Capture output as string
            with console.capture() as capture:
                console.print(table)
            return capture.get()
        except ImportError:
            # Plain text fallback
            lines = ["RAG Evaluation Results", "=" * 40]
            for metric, score in results.items():
                display_name = metric.replace("_", " ").title()
                lines.append(f"{display_name:.<30} {score:.4f}")
            return "\n".join(lines)
