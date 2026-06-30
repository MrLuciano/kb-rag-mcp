"""CSV loader for golden Q&A datasets.

Supports comma, semicolon, and tab delimiters.
Normalizes columns to the GoldenDataset format:
  query, expected_answer, expected_docs, metadata
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

log = logging.getLogger("kb-mcp.eval")

REQUIRED_COLUMNS = {"query", "expected_answer"}
OPTIONAL_COLUMNS = {"expected_docs", "metadata"}

DELIMITERS = [",", ";", "\t"]


class CSVDatasetLoader:
    """Load golden Q&A datasets from CSV files."""

    @staticmethod
    def load(path: Path) -> List[Dict[str, Any]]:
        """Load dataset from a CSV file.

        Args:
            path: Path to the CSV file.

        Returns:
            List of dicts with keys: query, expected_answer,
            expected_docs, metadata.

        Raises:
            ValueError: If required columns are missing
            or file is unreadable.
        """
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise ValueError(f"CSV file is empty: {path}")

        # Auto-detect delimiter
        delimiter = _detect_delimiter(text)
        log.debug("Detected delimiter for %s: %r", path, delimiter)

        reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
        fieldnames = set(reader.fieldnames or [])

        missing = REQUIRED_COLUMNS - fieldnames
        if missing:
            raise ValueError(
                f"Missing required columns in {path}: "
                f"{', '.join(sorted(missing))}"
            )

        examples: List[Dict[str, Any]] = []
        for row in reader:
            example: Dict[str, Any] = {
                "query": (row.get("query") or "").strip(),
                "expected_answer": (row.get("expected_answer") or "").strip(),
            }

            # Parse expected_docs (comma-separated list)
            docs_raw = row.get("expected_docs", "")
            if docs_raw.strip():
                example["expected_docs"] = [
                    d.strip() for d in docs_raw.split(",") if d.strip()
                ]
            else:
                example["expected_docs"] = []

            # Parse metadata (optional JSON string)
            meta_raw = row.get("metadata", "")
            if meta_raw.strip():
                try:
                    example["metadata"] = json.loads(meta_raw)
                except json.JSONDecodeError:
                    log.warning(
                        "Invalid JSON in metadata field: %r",
                        meta_raw,
                    )
                    example["metadata"] = {"raw": meta_raw.strip()}
            else:
                example["metadata"] = {}

            examples.append(example)

        log.info("Loaded %d examples from %s", len(examples), path)
        return examples


def _detect_delimiter(text: str) -> str:
    """Detect CSV delimiter by checking the first non-empty line."""
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if line:
            # Count occurrences of each candidate delimiter
            counts = {d: line.count(d) for d in DELIMITERS}
            # Prefer the delimiter with the most occurrences
            best = max(counts, key=lambda d: counts[d])
            if counts[best] > 0:
                return best
            break
    return ","
