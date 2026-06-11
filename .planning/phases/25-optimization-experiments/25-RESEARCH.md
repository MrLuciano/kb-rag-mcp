# Phase 25: Optimization Experiments — Research

**Researched:** 2026-06-11
**Domain:** RAG retrieval optimization, chunking strategies, scoring experiments, IR metrics
**Confidence:** HIGH

## Summary

Phase 25 delivers systematic experimentation capabilities for tuning RAG retrieval quality. The existing codebase has production-grade retrieval (hybrid dense+BM25 search with RRF fusion, cross-encoder reranking) and a complete RAGAS evaluation pipeline (Phase 24), but optimization is currently limited to two `NotImplementedError` stubs in `kb_server/optimization/`.

The research confirms that **all libraries required for this phase are already installed** — no new dependencies needed. The existing `langchain_text_splitters` (1.1.2) provides recursive, character, token, and language-aware splitters. `docling` (2.96.0) provides `HybridChunker` for semantic/layout-aware chunking. Qdrant natively supports four distance metrics (COSINE, DOT, EUCLID, MANHATTAN). The Phase 24 evaluation infrastructure (`GoldenDataset`, `RAGASEvaluator`, `ResultsExporter`, LLM wrappers) can be reused directly as the experiment harness.

**Primary recommendation:** Build an experiment runner that parameterizes chunking strategies and scoring configurations, runs them against a golden dataset, and produces comparable metrics (recall@K, MRR) using existing evaluation infrastructure. Store results in CSV/JSON for trend analysis.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Chunking strategy execution | Ingest Pipeline | — | Chunking happens at document ingestion time; experiments must re-ingest with different parameters |
| Scoring/reranking experiments | Query Server | — | Search and reranking happen at query time; experiments run live searches against indexed data |
| Metric computation | Query Server | Evaluation module | IR metrics (recall@K, MRR) computed from search results against golden dataset expectations |
| Result storage/comparison | Evaluation module | — | CSV/JSON export using existing `ResultsExporter`; trend comparison is offline analysis |
| Experiment orchestration | CLI / Evaluation | — | `kb-rag optimize` CLI subcommand following existing `kb-rag evaluate` pattern |

## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for this phase. Decisions are derived from REQUIREMENTS.md and existing codebase patterns.

### Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OPT-01 | User can run chunking experiments with configurable strategies (fixed, recursive, semantic) | `langchain_text_splitters` provides recursive/character/token splitters; `docling.chunking.HybridChunker` provides semantic/layout-aware chunking; manual fallback provides fixed-size chunking |
| OPT-02 | User can run scoring/reranking experiments comparing cross-encoder to other strategies | Qdrant supports COSINE/DOT/EUCLID/MANHATTAN distances; `HybridSearcher` has configurable `dense_weight`, `sparse_weight`, `rrf_k`; `CrossEncoderReranker` supports model swapping; reranking can be enabled/disabled for A/B comparison |
| OPT-03 | User can view comparison metrics (recall@K, MRR) across experiment runs | `GoldenDataset` provides `expected_docs` for recall computation; MRR pattern exists in `qa/report.py`; `sklearn.metrics.ndcg_score` available for NDCG; `ResultsExporter` handles CSV/JSON/console output |

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langchain-text-splitters` | 1.1.2 | Document chunking (recursive, character, token, language) | Already used in `ingest/ingest.py`; proven in production |
| `docling` | 2.96.0 | Semantic chunking via `docling.chunking.HybridChunker` | Installed for PDF extraction; extends chunking without new deps |
| `qdrant-client` | 1.18.0 | Vector search with configurable distance metrics | Entire retrieval pipeline depends on this |
| `sentence-transformers` | 5.5.0 | Cross-encoder reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`) | Already used in `reranker.py` |
| `fastembed` | 0.8.0 | BM25 sparse vectors for hybrid search | Already used in `hybrid_search.py` |
| `scikit-learn` | 1.8.0 | `ndcg_score` for ranking metrics | Already in requirements.txt |
| `matplotlib` | 3.10.9 | Evaluation visualizations | Already in requirements.txt |
| `rich` | 14.3.4 | Console tables for experiment results | Already used in CLI and `ResultsExporter` |

### Supporting (Already Installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pandas` | 3.0.3 | DataFrame manipulation for experiment result aggregation | For advanced result comparison tables |
| `pytest` | 9.0.3 | Test runner for experiment code | Follow existing test conventions |
| `pytest-asyncio` | 1.3.0 | Async test support | All experiment code is async |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `docling.chunking.HybridChunker` | Custom semantic chunker with sentence-transformers | HybridChunker is already installed and designed for document layouts; custom solution is unnecessary complexity |
| `sklearn.metrics.ndcg_score` | Custom NDCG implementation | sklearn is already installed and well-tested; custom implementation risks bugs |
| CSV result storage | SQLite trend storage | SQLite deferred per Phase 24 context; CSV is sufficient for v1.4 |

**Installation:** No new packages required — all dependencies are already in `requirements.txt` and `.venv/`.

## Package Legitimacy Audit

**No new packages required for this phase.** All functionality is built on existing, verified dependencies:

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| langchain-text-splitters | PyPI | 2+ yrs | 5M+/mo | github.com/langchain-ai | N/A (pre-installed) | Approved |
| docling | PyPI | 1+ yr | 500K+/mo | github.com/DS4SD/docling | N/A (pre-installed) | Approved |
| sentence-transformers | PyPI | 5+ yrs | 20M+/mo | github.com/UKPLab/sentence-transformers | N/A (pre-installed) | Approved |
| scikit-learn | PyPI | 15+ yrs | 100M+/mo | github.com/scikit-learn | N/A (pre-installed) | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Experiment CLI (kb-rag optimize)         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ chunk       │  │ scoring     │  │ compare           │  │
│  │ subcommand  │  │ subcommand  │  │ subcommand        │  │
│  └──────┬──────┘  └──────┬──────┘  └─────────────────────┘  │
└─────────┼────────────────┼───────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────┐  ┌─────────────────────┐
│ ChunkingEngine  │  │ ScoringEngine       │
│ (param sweep)   │  │ (param sweep)       │
└────────┬────────┘  └────────┬────────────┘
         │                    │
         ▼                    ▼
┌──────────────────────────────────────────┐
│  GoldenDataset + RAGASEvaluator          │
│  (reuse Phase 24 evaluation pipeline)    │
└────────────────────┬─────────────────────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
┌─────────────┐ ┌──────────┐ ┌─────────────┐
│ VectorStore │ │ Hybrid   │ │ CrossEncoder│
│ .search()   │ │ Searcher │ │ Reranker   │
│ (dense)     │ │ (dense+  │ │ (rerank)   │
│             │ │ sparse)  │ │             │
└─────────────┘ └──────────┘ └─────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│  MetricComputer                            │
│  - recall@K (expected_docs in results)   │
│  - MRR (mean reciprocal rank)              │
│  - NDCG (sklearn.ndcg_score)             │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│  ResultsExporter (CSV/JSON/Console)      │
│  (reuse Phase 24 exporter)               │
└──────────────────────────────────────────┘
```

### Recommended Project Structure

```
kb_server/optimization/
├── __init__.py                    # Package init
├── chunking_experiments.py        # Chunking strategy experiments (OPT-01)
├── scoring_experiments.py         # Scoring/reranking experiments (OPT-02)
├── experiment_runner.py         # Orchestrator: parameter sweep + evaluation
├── metric_computer.py             # IR metrics: recall@K, MRR, MAP, NDCG
├── result_store.py                # Experiment result persistence/comparison
└── config.py                      # Experiment parameter defaults

ingest/cli/
├── optimize.py                    # `kb-rag optimize` CLI entry point

tests/
├── test_optimization.py           # Expand existing stub tests
├── test_chunking_experiments.py   # Test chunking strategies
├── test_scoring_experiments.py    # Test scoring variations
└── test_metric_computer.py        # Test IR metric calculations
```

### Pattern 1: Parameter Sweep Experiment
**What:** Systematically vary one parameter (e.g., chunk size) while holding others constant, run evaluation against golden dataset, collect metrics.
**When to use:** All three requirements (OPT-01, OPT-02, OPT-03) require this pattern.
**Example:**
```python
# Source: Existing codebase patterns (ingest/ingest.py, kb_server/evaluation/)
async def run_chunking_experiment(
    dataset: GoldenDataset,
    strategy: str,  # "fixed", "recursive", "semantic"
    chunk_size: int,
    overlap: int,
    docs_path: Path,
) -> dict[str, float]:
    """Run one experiment configuration and return metrics."""
    # 1. Re-ingest with new chunking parameters
    await run_ingest(docs_path, clean=True, force=True)
    # 2. Evaluate retrieval quality
    evaluator = RAGASEvaluator(dataset=dataset, vector_store=store)
    ragas_scores = await evaluator.evaluate()
    # 3. Compute IR metrics
    ir_metrics = await compute_ir_metrics(dataset, store, top_k=5)
    return {**ragas_scores, **ir_metrics}
```

### Pattern 2: Strategy Abstraction
**What:** Abstract chunking strategies behind a common interface so the experiment runner can swap them without changing the pipeline.
**When to use:** OPT-01 requires comparing fixed, recursive, and semantic chunking.
**Example:**
```python
# Source: Inferred from existing code patterns
class ChunkingStrategy(ABC):
    @abstractmethod
    def split(self, text: str, file_type: str) -> list[str]:
        ...

class RecursiveStrategy(ChunkingStrategy):
    def split(self, text: str, file_type: str) -> list[str]:
        settings = CHUNK_SETTINGS.get(file_type, {"size": 600, "overlap": 80})
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings["size"],
            chunk_overlap=settings["overlap"],
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return splitter.split_text(text)

class SemanticStrategy(ChunkingStrategy):
    def split(self, text: str, file_type: str) -> list[str]:
        from docling.chunking import HybridChunker
        chunker = HybridChunker(max_tokens=512)
        # ... convert text to docling document, chunk, return texts
```

### Pattern 3: Experiment Result Comparison
**What:** Store results from multiple runs with metadata (timestamp, parameters, strategy), then compute deltas and produce comparison tables.
**When to use:** OPT-03 requires viewing metrics across experiment runs.
**Example:**
```python
# Source: Inferred from existing ResultsExporter patterns
class ExperimentResultStore:
    def save(self, run_id: str, params: dict, metrics: dict) -> None:
        row = {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat(),
            **params,
            **metrics,
        }
        # Append to CSV
        ...

    def compare(self, run_ids: list[str]) -> dict:
        # Load rows, compute deltas, return comparison table data
        ...
```

### Anti-Patterns to Avoid
- **Hard-coding experiment parameters in source code:** Use env vars or CLI flags so experiments are reproducible without code changes.
- **Running experiments against production collections:** Always use a dedicated experiment collection or `clean=True` re-ingest to avoid polluting production data.
- **Re-implementing IR metrics:** Use `sklearn.metrics.ndcg_score` and standard formulas for MRR/recall — custom implementations are error-prone.
- **Synchronous evaluation blocking the event loop:** Use `asyncio.to_thread()` or keep evaluation async, following the Phase 24 RAGASEvaluator pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chunking text | Custom splitter logic | `langchain_text_splitters.RecursiveCharacterTextSplitter` | Handles edge cases (Unicode, multi-byte chars, separator priority) that manual splitting misses |
| Semantic chunking | Custom sentence embedding + clustering | `docling.chunking.HybridChunker` | Already installed; does layout-aware semantic chunking with tokenizer-aware boundaries |
| NDCG computation | Manual ranking math | `sklearn.metrics.ndcg_score` | Well-tested, handles edge cases, vectorized |
| Reranking model | Custom cross-encoder training | `sentence_transformers.CrossEncoder` | Pre-trained models (ms-marco-MiniLM-L-6-v2) are state-of-the-art for reranking |
| BM25 sparse vectors | Custom TF-IDF implementation | `fastembed.SparseTextEmbedding` | Optimized for Qdrant sparse vector indexing, handles tokenization internally |
| Experiment result storage | Custom binary format | CSV/JSON via `ResultsExporter` | Human-readable, importable into pandas/spreadsheet, already implemented in Phase 24 |

**Key insight:** This phase is about orchestration and measurement, not implementing core NLP algorithms. The project already has all the heavy-duty libraries installed.

## Common Pitfalls

### Pitfall 1: Re-ingest Without Clean Flag
**What goes wrong:** Running a chunking experiment appends new chunks to existing ones, doubling the index and corrupting retrieval metrics.
**Why it happens:** Forgetting to pass `clean=True` to `run_ingest()` when switching chunking strategies.
**How to avoid:** The experiment runner must always set `clean=True` before re-ingesting, or use a dedicated temporary collection.
**Warning signs:** recall@K suddenly improves because there are duplicate chunks; `total_chunks` in stats is higher than expected.

### Pitfall 2: Embedding Mismatch After Re-ingest
**What goes wrong:** Changing chunk sizes changes the number of chunks, but embeddings are cached on disk — stale embeddings may be reused if the cache key doesn't include chunking parameters.
**Why it happens:** The `diskcache` layer in `embed_client.py` caches by text hash; if chunk text changes, the hash changes. But if experiment code bypasses the cache or uses a different key scheme, stale vectors get used.
**How to avoid:** Ensure the experiment runner either (a) clears the embedding cache before each run, or (b) uses cache keys that include chunking strategy/version.
**Warning signs:** Search results contain chunks that don't match the current chunking strategy's expected sizes.

### Pitfall 3: Non-Deterministic Reranker Scores
**What goes wrong:** Cross-encoder scores vary slightly across runs due to batching, model warmup, or hardware (GPU vs CPU). This makes A/B comparison noisy.
**Why it happens:** The reranker model is lazy-loaded; first invocation may have different behavior than subsequent ones. Batch size affects score normalization.
**How to avoid:** Warm up the model with a dummy query before the experiment. Fix `batch_size` and `top_k` for all runs. Use statistical significance tests (paired t-test) when comparing runs.
**Warning signs:** Same configuration run twice produces different MRR values.

### Pitfall 4: Confusing RAGAS Metrics with IR Metrics
**What goes wrong:** RAGAS metrics (faithfulness, answer_relevancy) measure end-to-end RAG quality, while IR metrics (recall@K, MRR) measure retrieval quality. Mixing them in the same comparison without labeling causes confusion.
**Why it happens:** Both are "evaluation metrics" but they measure different things. RAGAS requires LLM-as-judge; IR metrics are deterministic.
**How to avoid:** Present IR metrics separately from RAGAS metrics in output tables. Label columns clearly: `retrieval_recall@5` vs `ragas_faithfulness`.
**Warning signs:** Stakeholders ask why a chunking change improved recall but not faithfulness.

### Pitfall 5: Experiment Collection Polluting Production
**What goes wrong:** Running experiments against the default `kb_docs` collection modifies production data.
**Why it happens:** The experiment runner uses the default collection name from env vars.
**How to avoid:** Always override `QDRANT_COLLECTION` to a temporary name (e.g., `kb_docs_experiment_{timestamp}`) for experiment runs, and delete the collection afterward.
**Warning signs:** Production queries return unexpected results after an experiment run.

## Code Examples

### Computing recall@K
```python
# Source: Inferred from GoldenDataset expected_docs pattern
def recall_at_k(
    retrieved_docs: list[str],
    expected_docs: list[str],
    k: int = 5,
) -> float:
    """Fraction of expected docs found in top-k retrieved docs."""
    top_k = retrieved_docs[:k]
    found = sum(1 for doc in expected_docs if doc in top_k)
    return found / len(expected_docs) if expected_docs else 0.0
```

### Computing MRR
```python
# Source: qa/report.py pattern + standard IR definition
def mean_reciprocal_rank(
    retrieved_docs_per_query: list[list[str]],
    expected_docs_per_query: list[list[str]],
) -> float:
    """Mean Reciprocal Rank: average of 1/rank of first relevant result."""
    rr_sum = 0.0
    for retrieved, expected in zip(retrieved_docs_per_query, expected_docs_per_query):
        for rank, doc in enumerate(retrieved, start=1):
            if doc in expected:
                rr_sum += 1.0 / rank
                break
    return rr_sum / len(retrieved_docs_per_query) if retrieved_docs_per_query else 0.0
```

### Computing NDCG with sklearn
```python
# Source: sklearn documentation (verified via python3 -c)
from sklearn.metrics import ndcg_score
import numpy as np

# relevance: binary (1 if doc is expected, 0 otherwise)
relevance = np.array([[1, 0, 1, 0, 0]])  # 2 relevant docs in top-5
scores = np.array([[0.9, 0.8, 0.7, 0.6, 0.5]])  # retrieval scores
ndcg = ndcg_score(relevance, scores, k=5)
```

### Qdrant Distance Metric Switch
```python
# Source: Qdrant models (verified via python3 -c)
from qdrant_client.models import Distance

# Current default: Distance.COSINE
# Alternatives: Distance.DOT, Distance.EUCLID, Distance.MANHATTAN
# To use in experiment: create collection with different distance
await client.create_collection(
    collection_name="experiment_dot",
    vectors_config=VectorParams(size=dim, distance=Distance.DOT),
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual chunking (fixed size + overlap) | `RecursiveCharacterTextSplitter` with per-type settings | Phase 1 (initial ingest) | Better preservation of sentence/paragraph boundaries |
| Dense-only search | Hybrid dense + BM25 sparse with RRF fusion | Phase 12 | Improved recall on exact technical terms |
| No reranking | Cross-encoder reranker (ms-marco-MiniLM-L-6-v2) | Phase 12 | Improved precision and NDCG@5 |
| RAGAS library dependency | Custom LLM-as-judge metrics via `kb_server/evaluation/metrics.py` | Phase 24 | Avoids ragas transitive dependency conflicts; uses existing backends |

**Deprecated/outdated:**
- `server/` (legacy) package layout: replaced by `kb_server/` (canonical) — any new experiment code must go in `kb_server/`.
- `ragas` library (not installed): Phase 24 uses custom metrics instead to avoid dependency conflicts.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `docling.chunking.HybridChunker` is suitable for semantic chunking experiments | Standard Stack | If HybridChunker requires specific docling Document objects (not plain text), the semantic chunking strategy may need a preprocessing step |
| A2 | `sklearn.metrics.ndcg_score` is sufficient for NDCG computation | Code Examples | If the metric requires gains other than binary relevance, custom implementation may be needed |
| A3 | No new packages are needed for this phase | Standard Stack | If HybridChunker or any other needed API requires a newer docling version, an upgrade may be required |
| A4 | Experiment runs can safely use `clean=True` re-ingest | Common Pitfalls | If docs are very large, re-ingest may be too slow; may need dedicated experiment collection instead |
| A5 | Cross-encoder model scores are deterministic after warmup | Common Pitfalls | If scores remain non-deterministic, experiment comparison may need statistical testing |

## Open Questions

1. **How does `HybridChunker` handle plain text vs. docling Documents?**
   - What we know: `HybridChunker` is a pydantic model with `chunk()` method, designed for docling document layouts.
   - What's unclear: Whether it can accept raw text strings or requires a `docling.Document` object.
   - Recommendation: Prototype the semantic chunking strategy early in implementation to verify input requirements. If Document objects are required, add a lightweight conversion step.

2. **Should experiments run against a dedicated Qdrant collection or the default one?**
   - What we know: The default collection is `kb_docs` (env `QDRANT_COLLECTION`).
   - What's unclear: Whether production users expect experiments to be completely isolated.
   - Recommendation: Use a temporary collection per experiment run (e.g., `kb_docs_experiment_{run_id}`) and clean up afterward. This avoids all pollution risks.

3. **How to handle embedding cache invalidation during experiments?**
   - What we know: `embed_client.py` uses `diskcache` for embedding caching.
   - What's unclear: Whether the cache key includes enough metadata to distinguish experiment runs.
   - Recommendation: The experiment runner should clear the cache directory (`data/embed_cache/` or similar) or use a cache namespace per experiment.

4. **What is the baseline for comparison?**
   - What we know: The docs/RAG_EVALUATION.md mentions "The first evaluation run establishes the baseline."
   - What's unclear: Whether the baseline should be persisted automatically or manually saved.
   - Recommendation: The first experiment run with default parameters should be auto-saved as `baseline` in the result store, and subsequent runs should compute delta against it.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All | ✓ | 3.13 | — |
| Qdrant | Vector search | ✓ | Docker/latest | Embedded mode (QDRANT_PATH) |
| LM Studio / Ollama | Embedding backend | ✗ | — | None (required for live evaluation) |
| langchain-text-splitters | Chunking | ✓ | 1.1.2 | — |
| docling | Semantic chunking | ✓ | 2.96.0 | — |
| sentence-transformers | Reranker | ✓ | 5.5.0 | — |
| sklearn | NDCG metric | ✓ | 1.8.0 | — |

**Missing dependencies with no fallback:**
- LM Studio or Ollama embedding backend — evaluation experiments require a live embedding provider. The experiment CLI should fail gracefully with a clear message if no backend is reachable.

**Missing dependencies with fallback:**
- None — all other dependencies are installed.

## Validation Architecture

> `workflow.nyquist_validation` is explicitly `false` in `.planning/config.json`. Skipping this section per protocol.

## Security Domain

> `security_enforcement` is not explicitly set to false, but this phase is entirely offline experimentation with no auth, network exposure, or data handling beyond existing patterns. No new ASVS categories apply.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A (no auth layer) |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A |
| V5 Input Validation | yes | GoldenDataset validation already exists; experiment parameters should be validated (e.g., chunk_size > 0, overlap < chunk_size) |
| V6 Cryptography | no | N/A |

## Sources

### Primary (HIGH confidence)
- `kb_server/optimization/chunking_experiments.py` — Existing stub (confirmed: NotImplementedError)
- `kb_server/optimization/scoring_experiments.py` — Existing stub (confirmed: NotImplementedError)
- `kb_server/retrieval/hybrid_search.py` — Hybrid search implementation with RRF fusion (verified: dense_weight, sparse_weight, rrf_k are configurable)
- `kb_server/retrieval/reranker.py` — Cross-encoder reranker with lazy loading (verified: model_name, batch_size configurable)
- `kb_server/vector_store.py` — Qdrant abstraction with COSINE distance (verified: Distance enum via python3 -c)
- `ingest/ingest.py` — Chunking implementation with `RecursiveCharacterTextSplitter` (verified: per-type CHUNK_SETTINGS)
- `kb_server/evaluation/ragas_pipeline.py` — RAGASEvaluator with live VectorStore integration (verified: reuses existing backends)
- `kb_server/evaluation/dataset.py` — GoldenDataset with expected_docs (verified: supports JSON and CSV)
- `kb_server/evaluation/exporter.py` — ResultsExporter with CSV/JSON/console output (verified: already implemented)
- `kb_server/evaluation/metrics.py` — Custom LLM-as-judge metrics (verified: 4 core metrics implemented)
- `kb_server/evaluation/llm_wrapper.py` — Backend abstraction for LLM judge (verified: 4 backends supported)
- `qa/report.py` — MRR pattern already in use (verified: `data["mrr"]`)
- `pyproject.toml` — Test configuration (verified: pytest-asyncio strict mode, coverage 90%)
- `requirements.txt` — All required packages present (verified: langchain-text-splitters, docling, sentence-transformers, scikit-learn, matplotlib)

### Secondary (MEDIUM confidence)
- `docs/RAG_EVALUATION.md` — Documents baseline and +10% improvement target (official project doc)
- `.planning/phases/24-ragas-evaluation/24-CONTEXT.md` — Phase 24 context with RAGAS integration approach (verified: custom metrics, no ragas library)
- Qdrant official docs — Distance metrics: COSINE, DOT, EUCLID, MANHATTAN (verified via python3 -c import)

### Tertiary (LOW confidence)
- `docling.chunking.HybridChunker` API details — Verified import succeeds, but full API (text input vs Document input) not fully tested in this session. See Assumption A1.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified installed and importable
- Architecture: HIGH — existing codebase patterns are clear and reusable
- Pitfalls: MEDIUM — some pitfalls are inferred from common RAG patterns rather than observed failures in this codebase

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (stable stack, low change risk)
