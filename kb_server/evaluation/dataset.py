"""Golden dataset management for RAG evaluation.

Supports both JSON and CSV formats:
  - JSON: list of objects with query, expected_answer, expected_docs, metadata
  - CSV: rows with columns query, expected_answer, expected_docs, metadata
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from kb_server.evaluation.csv_loader import CSVDatasetLoader


class GoldenDataset:
    """Manages golden dataset for RAG evaluation.

    Dataset format (JSON or CSV):
    [
        {
            "query": "How to install SSL?",
            "expected_answer": "Configure SSL in server.xml...",
            "expected_docs": ["admin_guide_ch5.pdf"],
            "metadata": {"product": "AppServer", "version": "3.2"}
        }
    ]
    """

    def __init__(self, dataset_path: Path):
        """Initialize dataset from JSON or CSV file.

        Args:
            dataset_path: Path to .json or .csv file.

        Raises:
            ValueError: For unsupported file extensions.
        """
        self.dataset_path = Path(dataset_path)
        self.examples = self._load_dataset()

    def _load_dataset(self) -> List[Dict[str, Any]]:
        """Load dataset based on file extension."""
        if not self.dataset_path.exists():
            return []

        suffix = self.dataset_path.suffix.lower()
        if suffix == ".json":
            return self._load_json()
        elif suffix == ".csv":
            return CSVDatasetLoader.load(self.dataset_path)
        else:
            raise ValueError(
                f"Unsupported dataset format: {suffix}. "
                "Use .json or .csv"
            )

    def _load_json(self) -> List[Dict[str, Any]]:
        """Load dataset from JSON file."""
        with open(self.dataset_path, 'r') as f:
            return json.load(f)

    @classmethod
    def from_csv(cls, path: Path) -> "GoldenDataset":
        """Create a GoldenDataset from a CSV file.

        Args:
            path: Path to .csv file.

        Returns:
            GoldenDataset instance.
        """
        return cls(path)

    def __len__(self) -> int:
        """Return number of examples."""
        return len(self.examples)

    def __getitem__(self, index: int) -> Dict[str, Any]:
        """Get example by index."""
        return self.examples[index]

    def add_example(
        self,
        query: str,
        expected_answer: str,
        expected_docs: List[str],
        metadata: Optional[Dict[str, str]] = None
    ) -> None:
        """Add a new example to the dataset.

        Args:
            query: The search query
            expected_answer: Expected answer text
            expected_docs: List of expected source documents
            metadata: Optional metadata (product, version, etc.)
        """
        example = {
            'query': query,
            'expected_answer': expected_answer,
            'expected_docs': expected_docs,
            'metadata': metadata or {}
        }
        self.examples.append(example)

    def save(self) -> None:
        """Save dataset to JSON file."""
        with open(self.dataset_path, 'w') as f:
            json.dump(self.examples, f, indent=2)

    def validate(self) -> List[str]:
        """Validate dataset for common issues.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        for i, example in enumerate(self.examples):
            # Check required fields
            if not example.get('query'):
                errors.append(f"Example {i}: Empty query")
            if not example.get('expected_answer'):
                errors.append(f"Example {i}: Empty expected_answer")
            if not example.get('expected_docs'):
                errors.append(
                    f"Example {i}: Empty or missing expected_docs"
                )

            # Check types
            if not isinstance(example.get('expected_docs', []), list):
                errors.append(
                    f"Example {i}: expected_docs must be a list"
                )

        return errors
