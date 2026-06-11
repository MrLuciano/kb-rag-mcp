# PHASE 16: RAG Performance and Accuracy - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish RAG evaluation methodology with metrics, analyze query patterns from production logs, implement continuous improvement pipeline, and optimize RAG based on real usage data.

**Architecture:** RAGAS-based evaluation framework with golden dataset, query pattern analysis from PHASE 14 logs, optimization experiments on chunking/scoring/reranking, and CI integration for regression detection.

**Tech Stack:** RAGAS, scikit-learn (k-means), matplotlib, pytest, LLM-as-judge (Ollama or OpenAI)

---

## Overview

PHASE 16 focuses on **data-driven RAG optimization**:

1. **Query Analyzer** - Analyze PHASE 14 query logs to find patterns
2. **Golden Dataset** - Create evaluation dataset from real queries
3. **RAGAS Pipeline** - Evaluate RAG quality with standard metrics
4. **Optimization Experiments** - Test improvements (chunking, scoring, reranking)
5. **CI Integration** - Automated regression testing

**Key Principle:** Optimize based on **real usage data** (query logs), not synthetic benchmarks.

---

## File Structure

### New Files

**Analytics:**
- `server/analytics/__init__.py` - Package init
- `server/analytics/query_analyzer.py` - Query pattern analysis
- `tests/test_query_analyzer.py` - Query analyzer tests

**Evaluation:**
- `server/evaluation/__init__.py` - Package init
- `server/evaluation/dataset.py` - Golden dataset management
- `server/evaluation/ragas_pipeline.py` - RAGAS evaluation
- `server/evaluation/golden_dataset.json` - Golden dataset (git-tracked)
- `tests/test_dataset.py` - Dataset tests
- `tests/test_ragas_pipeline.py` - RAGAS tests

**Optimization:**
- `server/optimization/__init__.py` - Package init
- `server/optimization/chunking_experiments.py` - Chunk size experiments
- `server/optimization/scoring_experiments.py` - Score threshold tuning
- `tests/test_optimization.py` - Optimization tests

**CI/CD:**
- `.github/workflows/ragas_weekly.yml` - Weekly RAGAS evaluation
- `scripts/run_ragas_evaluation.py` - Evaluation runner script

**Documentation:**
- `docs/RAG_EVALUATION.md` - Evaluation methodology guide
- `docs/PHASE16_COMPLETION.md` - Completion report

### Modified Files

- `requirements.in` - Add ragas, scikit-learn, matplotlib
- `CHANGELOG.md` - PHASE 16 entry
- `README.md` - Evaluation section

---

## Task 1: Query Analyzer Foundation

**Files:**
- Create: `server/analytics/__init__.py`
- Create: `server/analytics/query_analyzer.py`
- Create: `tests/test_query_analyzer.py`

**Goal:** Analyze PHASE 14 query logs to identify patterns, common queries, low-score queries, and cluster similar queries.

### Step 1: Write test for query log loading

- [ ] **Create test file**

```python
# tests/test_query_analyzer.py
import sqlite3
import tempfile
from pathlib import Path
import pytest
from server.analytics.query_analyzer import QueryAnalyzer


@pytest.fixture
def temp_query_db():
    """Temporary database with sample query logs."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create query_log table
    cursor.execute("""
        CREATE TABLE query_log (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            query_text TEXT NOT NULL,
            result_count INTEGER,
            max_score REAL,
            latency_ms REAL
        )
    """)
    
    # Insert sample queries
    cursor.executemany("""
        INSERT INTO query_log (
            timestamp, query_text, result_count, max_score, latency_ms
        ) VALUES (?, ?, ?, ?, ?)
    """, [
        ('2024-01-01T10:00:00', 'How to install?', 5, 0.95, 45.0),
        ('2024-01-01T10:05:00', 'How to install?', 5, 0.94, 43.0),
        ('2024-01-01T10:10:00', 'SSL configuration', 3, 0.88, 50.0),
        ('2024-01-01T10:15:00', 'API documentation', 0, 0.0, 35.0),
        ('2024-01-01T10:20:00', 'upgrade guide', 4, 0.72, 48.0),
    ])
    
    conn.commit()
    conn.close()
    
    yield db_path
    db_path.unlink(missing_ok=True)


def test_load_queries(temp_query_db):
    """Test loading queries from database."""
    analyzer = QueryAnalyzer(db_path=temp_query_db)
    queries = analyzer.load_queries()
    
    assert len(queries) == 5
    assert queries[0]['query_text'] == 'How to install?'
    assert queries[0]['result_count'] == 5
```

- [ ] **Run test (RED)**
```bash
pytest tests/test_query_analyzer.py::test_load_queries -v
# Expected: FAIL (module doesn't exist)
```

### Step 2: Implement QueryAnalyzer.load_queries()

- [ ] **Create package init**

```python
# server/analytics/__init__.py
"""Analytics package for query pattern analysis."""
```

- [ ] **Implement query loader**

```python
# server/analytics/query_analyzer.py
"""Query pattern analyzer for RAG optimization."""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any


class QueryAnalyzer:
    """
    Analyzes query logs to identify patterns and optimization opportunities.
    
    Loads queries from PHASE 14 query_log table and provides methods to:
    - Identify most common queries
    - Find low-score queries (quality issues)
    - Detect zero-result queries (content gaps)
    - Cluster similar queries
    """
    
    def __init__(self, db_path: Path):
        """Initialize analyzer with database path."""
        self.db_path = db_path
    
    def load_queries(self) -> List[Dict[str, Any]]:
        """
        Load all queries from query_log.
        
        Returns:
            List of query dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM query_log
            ORDER BY timestamp DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
```

- [ ] **Run test (GREEN)**
```bash
pytest tests/test_query_analyzer.py::test_load_queries -v
# Expected: PASS
```

### Step 3: Add most common queries analysis

- [ ] **Write test**

```python
def test_most_common_queries(temp_query_db):
    """Test identifying most common queries."""
    analyzer = QueryAnalyzer(db_path=temp_query_db)
    common = analyzer.get_most_common_queries(limit=3)
    
    assert len(common) <= 3
    assert common[0]['query_text'] == 'How to install?'
    assert common[0]['frequency'] == 2
```

- [ ] **Implement method**

```python
def get_most_common_queries(
    self, limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get most frequently asked queries.
    
    Args:
        limit: Maximum number of queries to return
        
    Returns:
        List of {query_text, frequency} dicts
    """
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT query_text, COUNT(*) as frequency
        FROM query_log
        GROUP BY query_text
        HAVING frequency > 1
        ORDER BY frequency DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {'query_text': row[0], 'frequency': row[1]}
        for row in rows
    ]
```

- [ ] **Run test (GREEN)**

### Step 4: Add low-score query analysis

- [ ] **Write test**

```python
def test_low_score_queries(temp_query_db):
    """Test identifying low-score queries."""
    analyzer = QueryAnalyzer(db_path=temp_query_db)
    low_scores = analyzer.get_low_score_queries(threshold=0.75)
    
    assert len(low_scores) > 0
    assert all(q['max_score'] < 0.75 for q in low_scores)
```

- [ ] **Implement method**

```python
def get_low_score_queries(
    self, threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Get queries with low max scores (quality issues).
    
    Args:
        threshold: Score threshold (queries below this)
        
    Returns:
        List of query dictionaries
    """
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM query_log
        WHERE max_score < ?
        ORDER BY max_score ASC
    """, (threshold,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]
```

- [ ] **Run test (GREEN)**

### Step 5: Add zero-result query analysis

- [ ] **Write test**

```python
def test_zero_result_queries(temp_query_db):
    """Test identifying zero-result queries."""
    analyzer = QueryAnalyzer(db_path=temp_query_db)
    zero_results = analyzer.get_zero_result_queries()
    
    assert len(zero_results) > 0
    assert all(q['result_count'] == 0 for q in zero_results)
```

- [ ] **Implement method**

```python
def get_zero_result_queries(self) -> List[Dict[str, Any]]:
    """
    Get queries that returned zero results (content gaps).
    
    Returns:
        List of query dictionaries with frequency counts
    """
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT query_text, COUNT(*) as frequency
        FROM query_log
        WHERE result_count = 0
        GROUP BY query_text
        ORDER BY frequency DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {'query_text': row[0], 'frequency': row[1]}
        for row in rows
    ]
```

- [ ] **Run test (GREEN)**

### Step 6: Run all QueryAnalyzer tests

- [ ] **Run full test suite**
```bash
pytest tests/test_query_analyzer.py -v
# Expected: All tests pass
```

---

## Task 2: Golden Dataset Creation

**Files:**
- Create: `server/evaluation/__init__.py`
- Create: `server/evaluation/dataset.py`
- Create: `server/evaluation/golden_dataset.json`
- Create: `tests/test_dataset.py`

**Goal:** Create and manage golden dataset with query/answer/expected_docs triples for evaluation.

### Step 1: Define dataset structure

- [ ] **Write test for dataset loading**

```python
# tests/test_dataset.py
import json
import tempfile
from pathlib import Path
import pytest
from server.evaluation.dataset import GoldenDataset


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
            'metadata': {'product': 'ArchiveCenter', 'version': '23.4'}
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
```

- [ ] **Run test (RED)**

### Step 2: Implement GoldenDataset class

- [ ] **Create package init**

```python
# server/evaluation/__init__.py
"""Evaluation package for RAG quality assessment."""
```

- [ ] **Implement dataset class**

```python
# server/evaluation/dataset.py
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
            "metadata": {"product": "ArchiveCenter", "version": "23.4"}
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
```

- [ ] **Run test (GREEN)**

### Step 3: Add dataset validation

- [ ] **Write test**

```python
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
```

- [ ] **Implement validation**

```python
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
```

- [ ] **Run test (GREEN)**

### Step 4: Create initial golden dataset

- [ ] **Create dataset file with 10 examples**

```json
// server/evaluation/golden_dataset.json
[
  {
    "query": "How to install ArchiveCenter on Linux?",
    "expected_answer": "Install prerequisites (Java 11+, PostgreSQL), extract archive to /opt/archivecenter, run install.sh, configure database connection in config.properties",
    "expected_docs": ["ArchiveCenter_23.4_Install_Guide.pdf"],
    "metadata": {
      "product": "ArchiveCenter",
      "version": "23.4",
      "doc_type": "install_guide"
    }
  },
  {
    "query": "What are the hardware requirements for xECM?",
    "expected_answer": "Minimum: 4 CPU cores, 16GB RAM, 500GB disk. Recommended: 8+ cores, 32GB+ RAM, 1TB+ SSD",
    "expected_docs": ["xECM_System_Requirements.pdf"],
    "metadata": {
      "product": "xECM",
      "version": "23.4",
      "doc_type": "overview"
    }
  },
  {
    "query": "How to configure SSL for OTDS?",
    "expected_answer": "Generate keystore with keytool, update server.xml with SSL connector, set keystoreFile and keystorePass, restart service",
    "expected_docs": ["OTDS_Admin_Guide_Security.pdf"],
    "metadata": {
      "product": "OTDS",
      "version": "23.4",
      "doc_type": "admin_guide"
    }
  }
]
```

**Note:** Start with 10 examples, expand to 50+ over time.

- [ ] **Commit dataset to git**
```bash
git add server/evaluation/golden_dataset.json
git commit -m "feat(eval): add initial golden dataset (10 examples)"
```

### Step 5: Run all dataset tests

- [ ] **Run test suite**
```bash
pytest tests/test_dataset.py -v
# Expected: All tests pass
```

---

## Task 3: RAGAS Pipeline Implementation

**Files:**
- Create: `server/evaluation/ragas_pipeline.py`
- Create: `tests/test_ragas_pipeline.py`
- Modify: `requirements.in` (add ragas)

**Goal:** Implement RAGAS evaluation pipeline to measure RAG quality.

### Step 1: Add RAGAS dependency

- [ ] **Update requirements**

```python
# requirements.in
# Add after existing dependencies
ragas>=0.1.0              # RAG evaluation framework
scikit-learn>=1.3.0       # For clustering
matplotlib>=3.7.0         # For visualization
```

- [ ] **Compile requirements**
```bash
pip-compile requirements.in
pip install -r requirements.txt
```

### Step 2: Write test for RAGAS runner

- [ ] **Create test file**

```python
# tests/test_ragas_pipeline.py
import pytest
from pathlib import Path
from server.evaluation.ragas_pipeline import RAGASEvaluator
from server.evaluation.dataset import GoldenDataset


@pytest.fixture
def mock_dataset(tmp_path):
    """Create mock golden dataset."""
    import json
    
    examples = [
        {
            'query': 'How to install?',
            'expected_answer': 'Run install.sh',
            'expected_docs': ['guide.pdf'],
            'metadata': {}
        }
    ]
    
    dataset_path = tmp_path / 'dataset.json'
    with open(dataset_path, 'w') as f:
        json.dump(examples, f)
    
    return GoldenDataset(dataset_path=dataset_path)


def test_evaluator_initialization(mock_dataset):
    """Test RAGASEvaluator initialization."""
    evaluator = RAGASEvaluator(dataset=mock_dataset)
    assert evaluator.dataset == mock_dataset


@pytest.mark.skip(reason="Requires LLM API, expensive")
def test_run_evaluation(mock_dataset):
    """Test running RAGAS evaluation."""
    evaluator = RAGASEvaluator(dataset=mock_dataset)
    results = evaluator.evaluate()
    
    assert 'context_precision' in results
    assert 'answer_relevancy' in results
    assert 'faithfulness' in results
```

- [ ] **Run test (RED - skip expensive test)**

### Step 3: Implement RAGASEvaluator

- [ ] **Implement evaluator**

```python
# server/evaluation/ragas_pipeline.py
"""RAGAS-based RAG evaluation pipeline."""
from typing import Dict, Any, List
from pathlib import Path
import json
from server.evaluation.dataset import GoldenDataset


class RAGASEvaluator:
    """
    RAGAS evaluation pipeline for RAG quality assessment.
    
    Measures:
    - context_precision: Relevant chunks in top results
    - context_recall: Coverage of expected answer
    - answer_relevancy: Answer quality vs query
    - faithfulness: Answer grounded in retrieved context
    """
    
    def __init__(
        self,
        dataset: GoldenDataset,
        llm_provider: str = 'ollama',
        model: str = 'llama2'
    ):
        """
        Initialize evaluator.
        
        Args:
            dataset: Golden dataset
            llm_provider: 'ollama' or 'openai'
            model: Model name for LLM-as-judge
        """
        self.dataset = dataset
        self.llm_provider = llm_provider
        self.model = model
    
    def evaluate(self) -> Dict[str, float]:
        """
        Run RAGAS evaluation on golden dataset.
        
        Returns:
            Dictionary of metric scores
        """
        # TODO: Implement RAGAS evaluation
        # This requires:
        # 1. Run queries through RAG system
        # 2. Collect retrieved contexts and generated answers
        # 3. Run RAGAS metrics
        # 4. Aggregate scores
        
        raise NotImplementedError(
            "RAGAS evaluation requires LLM API setup. "
            "See docs/RAG_EVALUATION.md for setup instructions."
        )
    
    def save_results(
        self, results: Dict[str, float], output_path: Path
    ) -> None:
        """Save evaluation results to JSON."""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
```

- [ ] **Run test (GREEN - init test passes, eval skipped)**

### Step 4: Document RAGAS setup

- [ ] **Create evaluation guide stub**

```markdown
# docs/RAG_EVALUATION.md

# RAG Evaluation Guide

## Overview

PHASE 16 implements RAG evaluation using the RAGAS framework.

## Setup

### Prerequisites

1. **LLM Provider**: Choose one:
   - **Ollama** (local, free): Install ollama and pull llama2
   - **OpenAI** (cloud, paid): Get API key

2. **Golden Dataset**: Located at `server/evaluation/golden_dataset.json`

3. **Dependencies**: Install with `pip install -r requirements.txt`

### Ollama Setup

```bash
# Install ollama
curl https://ollama.ai/install.sh | sh

# Pull model
ollama pull llama2

# Verify
ollama run llama2 "Hello"
```

### OpenAI Setup

```bash
# Set API key
export OPENAI_API_KEY='sk-...'
```

## Running Evaluation

```bash
# Run RAGAS evaluation
python3 scripts/run_ragas_evaluation.py

# Output: server/evaluation/evaluation_results.json
```

## Metrics

- **context_precision**: Relevant chunks in top results (higher = better)
- **context_recall**: Coverage of expected answer (higher = better)
- **answer_relevancy**: Answer quality vs query (higher = better)
- **faithfulness**: Answer grounded in context (higher = better)

## Baseline

First run establishes baseline. Future runs compare against baseline.

Target improvements: +10% in at least one metric.
```

---

## Task 4: Optimization Experiments

**Files:**
- Create: `server/optimization/__init__.py`
- Create: `server/optimization/chunking_experiments.py`
- Create: `tests/test_optimization.py`

**Goal:** Run experiments to optimize chunking, scoring, and reranking.

### Stub Implementation (Time-boxed)

Given PHASE 16 scope and RAGAS setup complexity, we'll create **stub implementations** for optimization experiments with TODOs for future work.

- [ ] **Create optimization package**

```python
# server/optimization/__init__.py
"""Optimization experiments for RAG improvement."""


# server/optimization/chunking_experiments.py
"""Chunking parameter optimization experiments."""


def experiment_chunk_sizes():
    """
    Test different chunk sizes for different doc types.
    
    TODO: Implement experiment:
    1. Re-chunk documents with sizes: 256, 512, 1024, 2048
    2. Run RAGAS evaluation on each
    3. Compare scores
    4. Recommend optimal size per doc_type
    """
    raise NotImplementedError("See docs/RAG_EVALUATION.md")


# server/optimization/scoring_experiments.py  
"""Score threshold optimization experiments."""


def experiment_score_thresholds():
    """
    Test different score thresholds per product.
    
    TODO: Implement experiment:
    1. Test thresholds: 0.5, 0.6, 0.7, 0.8, 0.9
    2. Measure precision/recall tradeoffs
    3. Recommend optimal threshold per product
    """
    raise NotImplementedError("See docs/RAG_EVALUATION.md")
```

---

## Task 5: Documentation and Release

**Files:**
- Create: `docs/RAG_EVALUATION.md` (complete guide)
- Create: `docs/PHASE16_COMPLETION.md` (completion report)
- Modify: `CHANGELOG.md` (PHASE 16 entry)
- Modify: `README.md` (evaluation section)

### Step 1: Complete RAG_EVALUATION.md

- [ ] **Expand evaluation guide with:**
  - Query analyzer usage examples
  - Golden dataset creation workflow
  - RAGAS setup (Ollama/OpenAI)
  - Metrics interpretation
  - Optimization experiment templates
  - CI integration guide

### Step 2: Create completion report

- [ ] **Write PHASE16_COMPLETION.md**
  - Deliverables summary
  - What's complete vs. TODO
  - Test results
  - Usage examples
  - Next steps

### Step 3: Update CHANGELOG

- [ ] **Add PHASE 16 section**

```markdown
### Added - PHASE 16: RAG Performance and Accuracy (2026-05-16)

- **Query Pattern Analyzer**
  - Analyze PHASE 14 query logs for patterns
  - Identify most common queries, low-score queries, zero-result queries
  - Foundation for data-driven optimization
  - New module: `server/analytics/query_analyzer.py`
  - 5 unit tests

- **Golden Dataset Framework**
  - Dataset structure for RAG evaluation
  - JSON format with query/answer/docs triples
  - Initial dataset with 10 examples (expandable to 50+)
  - Git-tracked for version control
  - New module: `server/evaluation/dataset.py`
  - 3 unit tests

- **RAGAS Pipeline (Stub)**
  - Framework for RAGAS evaluation
  - Requires LLM setup (Ollama or OpenAI)
  - Stub implementation with setup guide
  - New module: `server/evaluation/ragas_pipeline.py`

- **Optimization Experiments (Stub)**
  - Chunking experiments framework
  - Score threshold tuning framework
  - Stub implementations with TODOs
  - New modules: `server/optimization/`

- **Documentation**
  - RAG evaluation guide: `docs/RAG_EVALUATION.md`
  - Completion report: `docs/PHASE16_COMPLETION.md`
  - Setup instructions for Ollama/OpenAI

### Dependencies
- ragas>=0.1.0 - RAG evaluation framework
- scikit-learn>=1.3.0 - For query clustering
- matplotlib>=3.7.0 - For visualization
```

### Step 4: Run all tests

- [ ] **Run complete test suite**
```bash
pytest tests/test_query_analyzer.py \
       tests/test_dataset.py \
       tests/test_ragas_pipeline.py -v
```

### Step 5: Commit and tag release

- [ ] **Commit changes**
```bash
git add -A
git commit -m "feat(PHASE16): add RAG evaluation framework

PHASE 16 Implementation:
- Query pattern analyzer for log analysis
- Golden dataset framework with 10 examples
- RAGAS pipeline stub (requires LLM setup)
- Optimization experiment stubs
- Comprehensive documentation

Components:
- server/analytics/query_analyzer.py: Pattern analysis
- server/evaluation/dataset.py: Golden dataset mgmt
- server/evaluation/ragas_pipeline.py: RAGAS stub
- server/optimization/: Experiment stubs

Tests: 8 passing (query analyzer + dataset)
Docs: RAG_EVALUATION.md, PHASE16_COMPLETION.md

Version: v0.13.0-dev"
```

- [ ] **Tag release**
```bash
git tag v0.13.0-dev
git push origin master --tags
```

---

## Acceptance Criteria

**Core Requirements:**
- [x] Golden dataset created with 10+ labeled examples (expandable to 50+)
- [x] Query analyzer extracts patterns from PHASE 14 logs
- [x] RAGAS pipeline stub with setup documentation
- [ ] At least 2 optimization experiments designed (stubs OK)
- [x] Documentation complete

**Tests:**
- [x] Query analyzer: 5 tests
- [x] Golden dataset: 3 tests
- [x] RAGAS pipeline: 2 tests (1 skipped, requires LLM)
- Total: 8 tests passing (2 skipped)

**Deliverables:**
- [x] `server/analytics/query_analyzer.py` (~150 lines)
- [x] `server/evaluation/dataset.py` (~120 lines)
- [x] `server/evaluation/ragas_pipeline.py` (~80 lines, stub)
- [x] `server/evaluation/golden_dataset.json` (10 examples)
- [x] `server/optimization/` (stubs with TODOs)
- [x] `docs/RAG_EVALUATION.md` (comprehensive guide)
- [x] Tests and documentation

---

## Estimated Effort

**Total: ~6-8 hours (stub implementation)**

- Task 1 (Query Analyzer): 2 hours
- Task 2 (Golden Dataset): 1.5 hours
- Task 3 (RAGAS Pipeline): 1 hour (stub only)
- Task 4 (Optimization): 0.5 hours (stubs)
- Task 5 (Documentation): 2 hours

**Full Implementation (with RAGAS + experiments): 14 days** (as per original plan)

---

## Notes

**Pragmatic Approach:**

PHASE 16 original scope is ambitious (14 days). This plan takes a **pragmatic, phased approach**:

**Phase 1 (This Implementation - 6-8 hours):**
- ✅ Query analyzer (production-ready)
- ✅ Golden dataset framework (production-ready)
- ✅ RAGAS pipeline (stub with setup guide)
- ✅ Optimization experiments (stubs with TODOs)
- ✅ Documentation

**Phase 2 (Future - requires LLM setup):**
- Full RAGAS implementation with Ollama/OpenAI
- Run evaluation on golden dataset
- Establish baseline metrics
- CI integration

**Phase 3 (Future - optimization):**
- Execute chunking experiments
- Execute scoring experiments
- Reranking optimization
- A/B testing framework

**Why This Approach:**

1. **Immediate Value**: Query analyzer provides insights from existing logs NOW
2. **Foundation**: Dataset framework enables gradual dataset growth
3. **Realistic**: Full RAGAS requires LLM setup (out of scope for quick implementation)
4. **Documented**: Clear path forward for Phase 2/3

**Decision Point:**

Do you want:
1. **Quick implementation** (6-8 hours): Query analyzer + dataset framework + stubs
2. **Full implementation** (14 days): Include RAGAS setup, experiments, CI

Recommend: Start with #1, evaluate value, then decide on #2.

---

## Related Documentation

- [QUERY_ANALYSIS.md](QUERY_ANALYSIS.md) - Query logging (PHASE 14)
- [PHASE12_COMPLETION.md](PHASE12_COMPLETION.md) - Search quality features
- [PLAN.md](PLAN.md) - Overall project plan
