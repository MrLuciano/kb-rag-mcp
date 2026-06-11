# RAG Evaluation Guide

## Overview

PHASE 16 implements RAG evaluation using the [RAGAS](https://docs.ragas.io/) framework. The goal is to measure and improve retrieval and answer quality based on real usage data from PHASE 14 query logs.

## Architecture

```
Query Logs (SQLite)
       │
       ▼
QueryAnalyzer          ←── server/analytics/query_analyzer.py
       │
       ▼
GoldenDataset          ←── server/evaluation/dataset.py
       │
       ▼
RAGASEvaluator         ←── server/evaluation/ragas_pipeline.py
       │
       ▼
Optimization Experiments ← server/optimization/
```

## Setup

### Prerequisites

1. **LLM Provider** — choose one:
   - **Ollama** (local, free): Install and pull a model
   - **OpenAI** (cloud, paid): Set `OPENAI_API_KEY`

2. **Golden Dataset** — `server/evaluation/golden_dataset.json`

3. **Dependencies** — already in `requirements.txt`

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
export OPENAI_API_KEY='sk-...'
```

## Running Query Analysis

```bash
# Analyze query patterns from PHASE 14 logs
python3 -c "
from server.analytics.query_analyzer import QueryAnalyzer
qa = QueryAnalyzer()
print(qa.most_common_queries(10))
print(qa.low_score_queries(threshold=0.5))
print(qa.zero_result_queries())
"
```

## Running RAGAS Evaluation

```bash
# Run RAGAS evaluation (requires LLM API)
python3 scripts/run_ragas_evaluation.py
# Output: server/evaluation/evaluation_results.json
```

## Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| `context_precision` | Relevant chunks in top results | > 0.80 |
| `context_recall` | Coverage of expected answer | > 0.75 |
| `answer_relevancy` | Answer quality vs query | > 0.85 |
| `faithfulness` | Answer grounded in context | > 0.80 |

## Golden Dataset

Located at `server/evaluation/golden_dataset.json`. Format:

```json
[
  {
    "query": "How to configure X?",
    "expected_answer": "Set X=value in config.yml",
    "expected_docs": ["config-guide.pdf"],
    "metadata": {"product": "product-a", "difficulty": "easy"}
  }
]
```

Add new examples from real user queries identified by `QueryAnalyzer`.

## Optimization Experiments

Stub implementations are in `server/optimization/`. Future work:

- **Chunk size tuning** — `chunking_experiments.py`: test 256/512/1024/2048 tokens
- **Score thresholds** — `scoring_experiments.py`: optimize per-product thresholds

## Baseline

The first evaluation run establishes the baseline. Subsequent runs compare against it. Target: +10% improvement in at least one metric per optimization cycle.

## CI Integration

A weekly GitHub Actions workflow (`.github/workflows/ragas_weekly.yml`) will run evaluations automatically. Results are committed as artifacts for trend analysis.
