"""Experiment result persistence and comparison.

PHASE 25: Optimization Experiments

Stores experiment runs as JSON files and supports CSV export,
run listing, and metric comparison across runs.
"""

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

log = logging.getLogger("kb-mcp.optimization")


class ExperimentResultStore:
    """Persist and compare experiment results.

    Each run is saved as a JSON file named ``{run_id}.json`` under
    *output_dir*.  The store also supports exporting summaries to CSV
    and loading/comparing historical runs.
    """

    def __init__(self, output_dir: Path = Path("data/experiments")):
        """Initialise the store, creating the output directory if needed.

        Args:
            output_dir: Directory where run JSON files are stored.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        log.info("ExperimentResultStore: %s", self.output_dir)

    def save(
        self,
        run_id: str,
        params: Dict[str, Any],
        metrics: Dict[str, Any],
        strategy: str,
        variant: str,
    ) -> Path:
        """Save an experiment run to JSON.

        Args:
            run_id: Unique identifier for the run.
            params: Experiment parameters used.
            metrics: Computed metric values.
            strategy: Chunking strategy name.
            variant: Scoring variant name.

        Returns:
            Path to the saved JSON file.
        """
        record = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc)
            .replace(tzinfo=None)
            .isoformat()
            + "Z",
            "strategy": strategy,
            "variant": variant,
            "params": params,
            "metrics": metrics,
        }
        path = self.output_dir / f"{run_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
        log.info("Saved experiment run: %s", path)
        return path

    def load(self, run_id: str) -> Dict[str, Any]:
        """Load a previously saved run.

        Args:
            run_id: Run identifier.

        Returns:
            Full run record as a dict.

        Raises:
            FileNotFoundError: If the run file does not exist.
        """
        path = self.output_dir / f"{run_id}.json"
        with open(path, "r", encoding="utf-8") as f:
            return cast(dict[str, Any], json.load(f))

    def list_runs(self) -> List[Dict[str, Any]]:
        """Return metadata for all stored runs, newest first.

        Returns:
            List of run metadata dicts (without the *metrics* field).
        """
        runs = []
        for path in sorted(
            self.output_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                runs.append(
                    {
                        "run_id": data.get("run_id", path.stem),
                        "timestamp": data.get("timestamp", ""),
                        "strategy": data.get("strategy", ""),
                        "variant": data.get("variant", ""),
                    }
                )
            except Exception as e:
                log.warning("Skipping unreadable run file %s: %s", path, e)
        return runs

    def compare(self, run_ids: List[str]) -> Dict[str, Any]:
        """Load specified runs and compute metric deltas.

        Args:
            run_ids: List of run identifiers to compare.

        Returns:
            Dict with keys:
            * ``runs`` — list of full run records.
            * ``deltas`` — dict mapping metric_name -> list of
              (run_id, value) tuples.
        """
        runs = []
        for rid in run_ids:
            try:
                runs.append(self.load(rid))
            except FileNotFoundError:
                log.warning("Run not found for comparison: %s", rid)

        # Collect all metric names
        metric_names = set()
        for run in runs:
            metric_names.update(run.get("metrics", {}).keys())

        deltas: Dict[str, List[tuple]] = {}
        for name in sorted(metric_names):
            deltas[name] = [
                (run["run_id"], run.get("metrics", {}).get(name))
                for run in runs
            ]

        return {"runs": runs, "deltas": deltas}

    def to_csv(self, output_path: Path) -> None:
        """Export all run summaries to CSV.

        Columns: ``run_id``, ``timestamp``, ``strategy``, ``variant``,
        plus one column per metric found across all runs.

        Args:
            output_path: Destination CSV file path.
        """
        runs = []
        metric_names = set()
        for path in sorted(self.output_dir.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                runs.append(data)
                metric_names.update(data.get("metrics", {}).keys())
            except Exception as e:
                log.warning("Skipping unreadable run file %s: %s", path, e)

        fieldnames = ["run_id", "timestamp", "strategy", "variant"] + sorted(
            metric_names
        )

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for run in runs:
                row = {
                    "run_id": run.get("run_id", ""),
                    "timestamp": run.get("timestamp", ""),
                    "strategy": run.get("strategy", ""),
                    "variant": run.get("variant", ""),
                }
                for name in metric_names:
                    row[name] = run.get("metrics", {}).get(name, "")
                writer.writerow(row)

        log.info("Exported %d runs to CSV: %s", len(runs), output_path)

    def baseline(self) -> Optional[Dict[str, Any]]:
        """Return the baseline run if one exists.

        A run with *run_id* == ``"baseline"`` is preferred; otherwise
        the oldest stored run is returned.

        Returns:
            Baseline run record, or ``None`` if no runs exist.
        """
        # Prefer explicit baseline
        baseline_path = self.output_dir / "baseline.json"
        if baseline_path.exists():
            with open(baseline_path, "r", encoding="utf-8") as f:
                return cast(dict[str, Any] | None, json.load(f))

        # Fallback to oldest run
        all_paths = sorted(
            self.output_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
        )
        if not all_paths:
            return None

        with open(all_paths[0], "r", encoding="utf-8") as f:
            return cast(dict[str, Any] | None, json.load(f))


# ── Convenience module-level helpers ────────────────────────────────


def load_results(
    output_dir: Path = Path("data/experiments"),
) -> List[Dict[str, Any]]:
    """Load all experiment results from *output_dir*.

    Args:
        output_dir: Directory containing run JSON files.

    Returns:
        List of full run records.
    """
    store = ExperimentResultStore(output_dir)
    return [store.load(r["run_id"]) for r in store.list_runs()]
