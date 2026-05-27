# Research Summary: v1.4 Evaluations & Docs

## Documentation Organization

- **Pattern:** Major RAG projects (NVIDIA, Intel) organize deployment docs by mode: Docker, Helm, Kubernetes, manual
- **Standard layout:** One file per deployment mode + shared troubleshooting/operations
- **Key insight:** README should link out to specialized docs, not contain all modes inline
- **Grouping:** Deployment modes (Compose/Helm/systemd) → Configuration → Operations → Troubleshooting → Reference

## RAGAS Evaluation Pipeline

- **Core metrics:** faithfulness, answer_relevancy, context_precision, context_recall
- **LLM-as-judge:** RAGAS uses configurable LLM to score responses against contexts + ground truth
- **Inputs needed:** question, answer, retrieved_contexts, ground_truth (for context_recall)
- **Minimum dataset:** 50 questions for stable signal; 100-200 comfortable
- **Hybrid strategy:** reference-free metrics on large sets, ground-truth metrics on curated 50-question core
- **Integration:** via `ragas.evaluate(dataset, metrics=[...])` with HuggingFace `datasets`
- **Already has:** `kb_server/evaluation/` with TODO placeholder at `ragas_pipeline.py:47`

## Chunking & Scoring Optimization

- **Multi-scale indexing:** Index same corpus at multiple chunk sizes (100, 200, 500 tokens); aggregate via RRF
- **Adaptive chunking:** Choose strategy per document based on intrinsic metrics (RC, ICC, DCC, BI, SC)
- **PPL chunking:** Perplexity-based boundary detection; +10-20% over fixed chunking
- **Evaluation metrics:** representability (does chunk contain answer?), recall@K, MRR, faithfulness
- **Chunking is the highest-impact decision:** Poor chunking cannot be recovered from downstream
- **Already has:** `kb_server/optimization/` with TODO placeholders at chunking_experiments.py:8, scoring_experiments.py:8

## Pitfalls

- Chunking optimization without fixing the retrieval/eval harness first gives misleading results
- RAGAS adds a new dependency and LLM cost — evaluate cost vs benefit
- Multi-chunk indexing multiplies storage and ingest time
- Documentation organization by deployment mode requires maintaining multiple parallel docs
