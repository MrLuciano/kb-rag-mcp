# Requirements: kb-rag-mcp

**Defined:** 2026-05-27
**Core Value:** AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.

## v1 Requirements

### Documentation

- [ ] **DOCS-01**: User can find docs organized by deployment mode (Docker Compose, Helm, systemd, manual) from README/OPERATIONS/TROUBLESHOOTING
- [ ] **DOCS-02**: Each deployment path has a dedicated doc file as single source of truth
- [ ] **DOCS-03**: CHANGELOG updated with all v1.3/v1.4 changes
- [ ] **DOCS-04**: REFERENCE.md updated with all v1.3/v1.4 changes

### RAGAS Evaluation

- [ ] **EVAL-01**: User can run RAGAS evaluation with 4 core metrics (faithfulness, answer_relevancy, context_precision, context_recall)
- [ ] **EVAL-02**: User can load golden Q&A dataset from CSV/JSON for evaluation
- [ ] **EVAL-03**: RAGAS evaluation reuses existing LM Studio/Ollama backend for LLM-as-judge scoring
- [ ] **EVAL-04**: User can export evaluation results as CSV with console summary table

### Optimization Experiments

- [ ] **OPT-01**: User can run chunking experiments with configurable strategies (fixed, recursive, semantic)
- [ ] **OPT-02**: User can run scoring/reranking experiments comparing cross-encoder to other strategies
- [ ] **OPT-03**: User can view comparison metrics (recall@K, MRR) across experiment runs

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time A/B testing in production | Experiments are offline/analysis only |
| Agentic chunking | Too experimental for this milestone |
| RAGAS metrics beyond 4 core | Keep evaluation focused; add later if needed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DOCS-01 | — | Pending |
| DOCS-02 | — | Pending |
| DOCS-03 | — | Pending |
| DOCS-04 | — | Pending |
| EVAL-01 | — | Pending |
| EVAL-02 | — | Pending |
| EVAL-03 | — | Pending |
| EVAL-04 | — | Pending |
| OPT-01 | — | Pending |
| OPT-02 | — | Pending |
| OPT-03 | — | Pending |

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 0
- Unmapped: 11

---

*Requirements defined: 2026-05-27*
*Last updated: 2026-05-27 after initial definition*
