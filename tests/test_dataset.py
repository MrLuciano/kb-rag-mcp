import json
import tempfile
from pathlib import Path
import pytest
from kb_server.evaluation.dataset import GoldenDataset


def test_load_empty_dataset():
    """Test loading an empty dataset."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    ) as f:
        json.dump([], f)
        dataset_path = Path(f.name)
    
    try:
        dataset = GoldenDataset(dataset_path=dataset_path)
        assert len(dataset) == 0
    finally:
        dataset_path.unlink()


def test_load_dataset_with_examples():
    """Test loading dataset with examples."""
    examples = [
        {
            'query': 'How to install SSL?',
            'expected_answer': 'Configure SSL in server.xml',
            'expected_docs': ['admin_guide_ch5.pdf'],
            'metadata': {'product': 'AppServer', 'version': '3.2'}
        }
    ]
    
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    ) as f:
        json.dump(examples, f)
        dataset_path = Path(f.name)
    
    try:
        dataset = GoldenDataset(dataset_path=dataset_path)
        assert len(dataset) == 1
        assert dataset[0]['query'] == 'How to install SSL?'
    finally:
        dataset_path.unlink()


def test_validate_dataset():
    """Test dataset validation."""
    examples = [
        {
            'query': 'How to install SSL?',
            'expected_answer': 'Configure SSL',
            'expected_docs': ['guide.pdf'],
            'metadata': {}
        },
        {
            'query': '',  # Invalid: empty query
            'expected_answer': 'Answer',
            'expected_docs': ['doc.pdf'],
            'metadata': {}
        }
    ]
    
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False
    ) as f:
        json.dump(examples, f)
        dataset_path = Path(f.name)
    
    try:
        dataset = GoldenDataset(dataset_path=dataset_path)
        errors = dataset.validate()
        assert len(errors) == 1
        assert 'empty query' in errors[0].lower()
    finally:
        dataset_path.unlink()

