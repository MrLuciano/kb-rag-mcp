# QA Review — Evaluation Corpus

**Date:** 2026-05-16
**Status:** Approved, pending implementation
**Author:** brainstorming session

---

## 1. Goal

Execute a full Quality Assurance review of the kb-rag-mcp RAG pipeline using a
production documentation corpus as real-world input.

**Primary goal (A):** End-to-end pipeline validation — ingest the full evaluation corpus,
run 20 representative queries, measure whether the system retrieves the right
documents with good scores. Confirm the pipeline works with real data.

**Secondary goal (B):** Heuristic RAGAS-lite metrics — compute Hit Rate, MRR, score
distribution, zero-result rate, and latency percentiles. Store retrieved contexts
in the golden dataset for future LLM-as-judge evaluation (no LLM judge in this run).

---

## 2. Inputs

| Input | Value |
|---|---|
| Corpus path | `/mnt/c/Users/luciano.marinho/git/corpus` |
| Document count | 271 files (PDF, DOCX, PPTX) across version subdirs + root |
| Product tag | `docs` |
| Embedding backend | FastEmbed (built-in, no external server) |
| Qdrant | Docker (`docker run -d --rm -p 6333:6333 qdrant/qdrant`) |
| LLM judge | None (heuristics only) |

---

## 3. Architecture

```
qa/
├── run_qa.py              # Orchestrator — single entry point
├── queries.json           # 20 curated queries with expected metadata
├── fixtures/              # 5-doc tiny PDF fixture corpus for integration tests
│   └── *.pdf
└── __init__.py

docs/
└── QA_REPORT.md           # Generated output (committed after run)

server/evaluation/
└── golden_dataset.json    # Replaced: 20 real Q&A pairs (was synthetic)
```

### Orchestrator stages (`run_qa.py`)

1. **Preflight** — verify Docker available, `.venv` active, `CORPUS_PATH` exists
2. **Qdrant** — `docker run -d --rm -p 6333:6333 qdrant/qdrant`, poll `/healthz`
3. **Ingest** — call `ingest.py` programmatically (full corpus, `BACKEND=fastembed`, `product=docs`, `workers=4`)
4. **Probe** — run 20 queries via `store.search()` directly, collect results + latency
5. **Metrics** — compute heuristic RAGAS-lite metrics
6. **Report** — write `docs/QA_REPORT.md`
7. **Golden dataset** — overwrite `server/evaluation/golden_dataset.json` with 20 real entries

### Entry point

```bash
python qa/run_qa.py [--corpus-path PATH] [--workers N] [--skip-ingest]
```

`--skip-ingest` allows re-running the probe/metrics/report against an already-ingested collection.

---

## 4. Query Set (`qa/queries.json`)

20 queries across 7 categories. Each entry:

```json
{
  "id": "install-01",
  "category": "installation",
  "query": "How to install AppServer 22.1 on Windows 2016?",
  "expected_doc_keywords": ["install", "22.1", "windows"],
  "min_expected_score": 0.5
}
```

### Categories and distribution

| Category | Count | Representative query |
|---|---|---|
| Installation | 4 | "How to install AppServer 22.1 on Windows 2016?" |
| Administration | 4 | "How to configure AppServer cluster management?" |
| Search & Index | 3 | "How does the Search Engine work in version 22?" |
| Workflow & Forms | 3 | "What are best practices for workflow design?" |
| SDK & Development | 3 | "How to use the SDK schema reference?" |
| WebReports | 2 | "How to design WebReports in version 20.2?" |
| Records Management | 1 | "How does Records Management work in AppServer?" |

---

## 5. Metrics & Pass/Fail Criteria

### Per-query metrics

- **Hit** — boolean: ≥1 result's `source_file` contains at least one `expected_doc_keywords` substring (case-insensitive)
- **Reciprocal Rank** — `1/rank` of first hit among top-5 (0 if no hit)
- **Top score** — highest cosine similarity in result set
- **Latency ms** — wall-clock time for `store.search()` call

### Aggregate metrics

| Metric | Definition | Pass threshold |
|---|---|---|
| **Hit Rate @5** | % of queries with hit=True | ≥ 70% |
| **MRR @5** | Mean of reciprocal ranks | ≥ 0.50 |
| **Zero-result rate** | % of queries with 0 results | ≤ 10% |
| **Score p50** | Median top-score across queries | ≥ 0.45 |
| **Score p95** | 95th-percentile top-score | ≥ 0.65 |
| **Latency p50** | Median query latency (ms) | ≤ 500 ms |
| **Latency p95** | 95th-percentile latency (ms) | ≤ 2000 ms |

**Overall verdict:** PASS if Hit Rate, MRR, zero-result rate, and score p50 all meet
threshold simultaneously. Any single failure → FAIL with labeled reason(s).

### Goal B bridge

For each query, the runner stores `retrieved_contexts` (top-5 chunk texts) in the
golden dataset JSON. When an LLM judge is available later, the RAGAS pipeline can
consume these without re-running ingestion.

---

## 6. Testing Strategy

### Unit tests (no Docker, no Qdrant, no real files)

| File | Coverage |
|---|---|
| `tests/test_qa_metrics.py` | `compute_hit_rate`, `compute_mrr`, `compute_score_stats`, `compute_latency_stats` — pure functions |
| `tests/test_qa_queries.py` | `queries.json` schema validation — required fields present, no empty keyword lists |
| `tests/test_qa_report.py` | Report renderer — fixed metrics dict → markdown contains required sections and verdict string |

### Integration test (Docker required, opt-in)

| File | Coverage |
|---|---|
| `tests/test_qa_integration.py` | Full pipeline: 5-doc fixture corpus → ingest → query → metrics → report file written. Skipped unless `QA_INTEGRATION=1`. |

### TDD order

1. Metrics functions (RED → GREEN) — `test_qa_metrics.py`
2. Query schema validator — `test_qa_queries.py`
3. Report renderer — `test_qa_report.py`
4. Integration test written (RED) before orchestrator implemented
5. Orchestrator implemented (GREEN)

### Constraint

`run_qa.py` imports from `ingest/` and `server/` but adds no side effects to
production modules. Existing test suite stays green.

---

## 7. Report Format (`docs/QA_REPORT.md`)

```markdown
# KB-RAG-MCP QA Report — Evaluation Corpus
Date: ...   Corpus: 271 docs   Backend: fastembed   Model: ...

## Overall Verdict: PASS / FAIL
Reason: ...

## Aggregate Metrics
| Metric         | Value  | Threshold | Status |
...

## Per-Query Results
| ID         | Category | Query (truncated)        | Hit | Rank | Score | Latency ms |
...

## Zero-Result Queries
...

## Recommendations
...
```

---

## 8. Golden Dataset Update

After the probe run, `server/evaluation/golden_dataset.json` is overwritten with
20 entries in this schema:

```json
{
  "query": "How to install AppServer 22.1 on Windows 2016?",
  "expected_answer": "(top chunk text, first 400 chars)",
  "expected_docs": ["<source_file of rank-1 result>"],
  "retrieved_contexts": ["<chunk text 1>", "...", "<chunk text 5>"],
  "metadata": {
    "product": "docs",
    "category": "installation",
    "hit": true,
    "top_score": 0.82
  }
}
```

This replaces the 10 synthetic examples with real ground truth.

---

## 9. Constraints & Non-Goals

- No authentication (internal use, consistent with project policy)
- No LLM judge in this run (deferred to future RAGAS implementation)
- No changes to production server code — QA is a separate `qa/` module
- `--skip-ingest` flag allows iterating on queries/metrics without re-ingesting
- Ingest estimated time: 20–40 min (271 docs, FastEmbed, 4 workers)
- Full test coverage of metrics/report logic; integration test is opt-in
