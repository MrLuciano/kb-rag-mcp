# Phase 24: RAGAS Evaluation Pipeline — Context

**Gathered:** 2026-05-30
**Updated:** 2026-05-31
**Status:** Ready for execution
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
- **Evaluation entry point**: `kb-rag evaluate` CLI subcommand (consistent with existing `kb-rag reclassify` pattern)
- **Async pattern**: Wrap sync RAGAS metrics in `asyncio.to_thread()` to avoid blocking the async event loop; VectorStore.search() remains async
- **RAGAS version**: Pin `ragas==0.2.14` — verified compatible with pydantic v2 (used by project)
- **Dataset ground_truth**: Require ground_truth for all datasets; skip metrics silently if ground_truth missing per-example rather than failing entire run
- **LLM judge backend**: Use same `EMBED_BACKEND` configuration as the main app (no separate `EVAL_BACKEND` for v0.1.4 simplicity)
- **Result persistence**: CSV + console table only for v0.1.4; SQLite trend storage deferred to future phase

### the agent's Discretion
- Exact CSV column names and delimiter detection thresholds
- Console table styling (rich vs plain text fallback)
- Whether to run metrics sequentially or in parallel batches
- Default dataset path when --dataset not provided
- Error handling strategy when LLM backend is unreachable during evaluation

### Recent Codebase Changes (2026-05-30 ad-hoc session)
The following changes were made to files referenced by Phase 24 plans and should be accounted for during execution:

1. **embed_client.py**: Cache metric names fixed (`cache_hits`/`cache_misses` with `backend="lru"` label). `import time` added. Batch embedding metrics now wired (`record_batch_embedding()`).
2. **vector_store.py**: Batch upsert metrics wired (`record_batch_upsert()`). `import time` added.
3. **server.py**: Query metrics wired (`record_query()`, `record_query_error()` in `call_tool()`).
4. **observability/metrics.py**: New metrics added: `kb_rag_query_duration_seconds`, `kb_rag_query_errors_total`.
5. **Grafana dashboard**: Rebuilt to only show live metrics. Ingest panels removed (jobs, files, workers) — these metrics exist but are not wired in ingest pipeline.
6. **CONCERNS.md**: Updated with current audit (6 issues resolved, 4 new issues added).
7. **AGENTS.md**: Personal info removed; project context kept.
8. **.planning/backlog.md**: Created with session context and pending items.

**Implication for Phase 24**: The evaluation pipeline should follow the same metrics wiring pattern used for query metrics (server.py) and batch metrics (embed_client.py, vector_store.py). If evaluation emits its own metrics, use `observability.metrics` module and ensure metric names match dashboard queries.

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `kb_server/evaluation/ragas_pipeline.py` — existing stub (NotImplementedError)
- `kb_server/evaluation/dataset.py` — existing GoldenDataset class
- `kb_server/embed_client.py` — embedding backend abstraction (must be reused). **Recently updated (2026-05-30):** batch metrics wired, cache metric names fixed, `import time` added
- `kb_server/server.py` — MCP server with search_kb tool (evaluation target). **Recently updated (2026-05-30):** query metrics wired in `call_tool()`
- `kb_server/vector_store.py` — direct Qdrant search (alternative evaluation target). **Recently updated (2026-05-30):** batch upsert metrics wired
- `observability/metrics.py` — Prometheus metrics definitions. **Recently updated (2026-05-30):** added `kb_rag_query_duration_seconds`, `kb_rag_query_errors_total`

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
- Weekly CI automation (mentioned in docs/RAG_EVALUATION.md but not in v0.1.4 requirements)
- QueryAnalyzer integration (PHASE 14 logs → golden dataset generation)

---

*Phase: 24-ragas-evaluation*
*Context gathered: 2026-05-30 via requirements + codebase analysis*
