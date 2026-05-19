"""Golden dataset management for RAG evaluation."""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class GoldenDataset:
    """
    Manages golden dataset for RAG evaluation.
    
    Dataset format:
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
        """Initialize dataset from JSON file."""
        self.dataset_path = dataset_path
        self.examples = self._load_dataset()
    
    def _load_dataset(self) -> List[Dict[str, Any]]:
        """Load dataset from JSON file."""
        if not self.dataset_path.exists():
            return []
        
        with open(self.dataset_path, 'r') as f:
            return json.load(f)
    
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
        """
        Add a new example to the dataset.
        
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
        """
        Validate dataset for common issues.
        
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

