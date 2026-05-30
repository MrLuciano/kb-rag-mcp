# Phase 24: RAGAS Evaluation Pipeline — Context

**Gathered:** 2026-05-30
**Status:** Ready for planning
**Source:** REQUIREMENTS.md (EVAL-01/02/03/04) + existing codebase analysis

## Phase Boundary

This phase delivers a complete RAGAS evaluation pipeline that measures RAG quality using 4 core metrics (faithfulness, answer_relevancy, context_precision, context_recall). The pipeline must:

1. Load golden Q&A datasets from CSV/JSON
2. Run RAGAS evaluation against the live kb-rag-mcp query pipeline
3. Use the existing LM Studio/Ollama backend as LLM-as-judge
4. Export results as CSV with console summary table

## Implementation Decisions

### Locked Decisions
- **RAGAS library**: Use `ragas==0.2.x` (latest stable) — industry standard, already documented in `docs/RAG_EVALUATION.md`
- **LLM backend**: Reuse existing `kb_server/embed_client.py` backends (lmstudio-sdk, lmstudio-rest, openai-compat, ollama) — EVAL-03 requirement
- **Dataset format**: Support both JSON (existing `GoldenDataset`) and CSV (new requirement EVAL-02)
- **Output format**: CSV export + console table (rich library, existing dependency) — EVAL-04 requirement
- **Metrics**: faithfulness, answer_relevancy, context_precision, context_recall — EVAL-01 requirement
- **Integration point**: Evaluation runs against live `kb_server/server.py` search_kb tool or direct VectorStore queries

### the agent's Discretion
- Exact RAGAS version to pin (need to check compatibility with async patterns)
- Whether to implement async evaluation (parallel metric computation) vs sync
- CLI command name (`kb-rag evaluate` or standalone script)
- Whether to cache evaluation results to SQLite (kb_metadata.db) or just CSV files
- How to handle the 4 metrics: RAGAS built-in vs custom implementations

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `kb_server/evaluation/ragas_pipeline.py` — existing stub (NotImplementedError)
- `kb_server/evaluation/dataset.py` — existing GoldenDataset class
- `kb_server/embed_client.py` — embedding backend abstraction (must be reused)
- `kb_server/server.py` — MCP server with search_kb tool (evaluation target)
- `kb_server/vector_store.py` — direct Qdrant search (alternative evaluation target)

### Documentation
- `docs/RAG_EVALUATION.md` — existing RAGAS guide (needs path updates server/ → kb_server/)
- `docs/AMDGPURESEARCH.md` — AMD GPU research (relevant for Ollama backend performance)

### Dependencies
- `requirements.txt` — RAGAS not yet present, needs pinning
- `setup.py` — entry points for CLI commands

## Specific Ideas

### RAGAS Integration Approach
RAGAS requires:
- `question` (query string)
- `answer` (generated answer)
- `contexts` (retrieved chunks list)
- `ground_truth` (expected answer)

Our pipeline needs to:
1. Load dataset example
2. Run `search_kb` or `VectorStore.search()` to get contexts
3. Generate answer (optional — could use existing query pipeline)
4. Run RAGAS metrics
5. Collect scores

### CSV Export Format
```csv
query,faithfulness,answer_relevancy,context_precision,context_recall,timestamp
"How to install?",0.85,0.92,0.78,0.88,2026-05-30T10:00:00Z
```

### Console Summary Table
```
┌─────────────────────────┬─────────┬─────────┬─────────┬─────────┐
│ Metric                  │ Mean    │ Min     │ Max     │ Count   │
├─────────────────────────┼─────────┼─────────┼─────────┼─────────┤
│ faithfulness            │ 0.82    │ 0.45    │ 0.98    │ 50      │
│ answer_relevancy        │ 0.91    │ 0.67    │ 0.99    │ 50      │
│ context_precision       │ 0.76    │ 0.30    │ 0.95    │ 50      │
│ context_recall          │ 0.84    │ 0.52    │ 0.97    │ 50      │
└─────────────────────────┴─────────┴─────────┴─────────┴─────────┘
```

## Deferred Ideas

- Real-time A/B testing in production (out of scope per REQUIREMENTS.md)
- RAGAS metrics beyond 4 core (out of scope)
- Weekly CI automation (mentioned in docs/RAG_EVALUATION.md but not in v1.4 requirements)
- QueryAnalyzer integration (FASE 14 logs → golden dataset generation)

---

*Phase: 24-ragas-evaluation*
*Context gathered: 2026-05-30 via requirements + codebase analysis*
