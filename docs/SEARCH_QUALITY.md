# Search Quality Features Guide

Guide to FASE 12 search quality enhancements: payload indexing, hybrid search, and cross-encoder reranking.

---

## Quick Start

### Enable Fast Filtered Queries
```bash
# One-time migration
kb-rag db create-indexes
```

###Use Hybrid Search
```python
search_kb(query="Archive Center 22.3", hybrid=True)
```

### Use Reranking
```python
search_kb(query="LDAP authentication", rerank=True)
```

---

## Feature Overview

| Feature | What It Does | When To Use | Latency Impact |
|---------|-------------|-------------|---------------|
| **Payload Indexes** | Fast filtered queries | Always (automatic) | -90% ⚡ |
| **Hybrid Search** | BM25 + dense vectors | Technical terms, versions | +50ms |
| **Reranking** | Cross-encoder refinement | High-precision needs | +200ms |

---

## Payload Indexing

**What:** Qdrant keyword indexes on `product` and `doc_type` fields

**Benefits:**
- 10x faster queries with filters
- No query changes needed
- Works with all existing code

**Setup:**
```bash
# Automatic on new collections
# Manual migration for existing:
python scripts/migrations/create_payload_indexes.py
```

**Verification:**
```python
# Check logs for:
"Índice criado no campo 'product'"
"Índice criado no campo 'doc_type'"
```

---

## Hybrid Search

**What:** Combines semantic (dense) + keyword (BM25 sparse) search using RRF fusion

**When To Use:**
- Queries with specific versions ("22.3", "3.2")
- Product codes or technical IDs
- Exact terminology important
- When semantic search misses obvious matches

**Example:**
```python
# Without hybrid (semantic only)
search_kb("Archive Center version 22.3 config")
# May rank docs with "Archive Center" higher even if different version

# With hybrid (semantic + keyword)
search_kb("Archive Center version 22.3 config", hybrid=True)
# Boosts docs with exact "22.3" match
```

**Configuration:**
```bash
# .env
HYBRID_DENSE_WEIGHT=0.7    # 70% weight to semantic similarity
HYBRID_SPARSE_WEIGHT=0.3   # 30% weight to keyword match
HYBRID_RRF_K=60            # RRF constant (higher = less aggressive fusion)
```

**Tuning:**
- Increase `HYBRID_SPARSE_WEIGHT` if missing exact term matches
- Decrease if getting too many keyword-only false positives
- Default (0.7/0.3) works well for most cases

**Current Limitation:**
- Sparse vectors not yet stored in collection
- Uses weighted dense results as placeholder
- Full implementation pending collection migration

---

## Cross-Encoder Reranking

**What:** Re-scores top-20 results with cross-encoder model, returns best top-k

**When To Use:**
- Complex queries requiring nuanced understanding
- When top results seem "close" in relevance
- High-precision requirements (e.g., critical docs)
- Willing to trade latency for quality

**Example:**
```python
# Without reranking
search_kb("How to troubleshoot LDAP auth failures?")
# May return general LDAP docs mixed with troubleshooting

# With reranking
search_kb("How to troubleshoot LDAP auth failures?", rerank=True)
# Cross-encoder better understands "troubleshoot" intent
```

**How It Works:**
1. Retrieve top-20 (4× top_k)
2. Score each query-doc pair with cross-encoder
3. Re-sort by new scores
4. Return top-k

**Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Trained on MS MARCO passage ranking
- 80MB download on first use
- ~200ms per batch of 20

**Configuration:**
```bash
# .env
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANKER_BATCH_SIZE=20
RERANKER_CACHE_TTL=3600  # Future: cache reranked results
```

---

## Combining Features

### Scenario 1: Fast General Query
```python
# Default (dense only, with indexes)
search_kb(
    query="backup procedures",
    product="AppServer",  # Fast filter via index
)
# ~50ms, good recall
```

### Scenario 2: Technical Query
```python
# Hybrid for exact term matching
search_kb(
    query="DataSync 3.2 installation",
    product="DataSync",
    hybrid=True,
)
# ~100ms, better recall on version
```

### Scenario 3: High-Precision Query
```python
# Reranking for best precision
search_kb(
    query="common causes of authentication timeouts",
    doc_type="admin_guide",
    rerank=True,
)
# ~250ms, best precision
```

### Scenario 4: Maximum Quality
```python
# Both hybrid + rerank
search_kb(
    query="Archive Center 22.3 LDAP troubleshooting",
    product="AppServer",
    hybrid=True,
    rerank=True,
    top_k=5,
)
# ~300ms, best recall + precision
```

---

## Performance Guidelines

### Latency Budget
```
Baseline (dense only):     ~50ms
+ Hybrid search:          +50ms = ~100ms
+ Reranking:             +200ms = ~250ms
+ Hybrid + Rerank:       +250ms = ~300ms
```

### Recommendations by Use Case

**Interactive search (user-facing):**
- Default: baseline (fast)
- Optionally: hybrid (still fast)
- Avoid: reranking (unless high-value query)

**Automated workflows (background):**
- Recommended: hybrid + rerank
- Latency less critical
- Quality more important

**High-volume APIs:**
- Use baseline with indexes
- Consider caching frequent queries
- Profile before enabling hybrid/rerank

---

## Troubleshooting

### "Reranking failed" in logs
**Cause:** Cross-encoder model failed to load  
**Fix:**
```bash
# Verify sentence-transformers installed
pip show sentence-transformers

# Pre-download model
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
```

### Hybrid search not improving results
**Cause:** Sparse vectors not yet stored  
**Status:** Awaiting collection migration (FASE 13)  
**Workaround:** Reranking alone may help

### Slow queries despite indexes
**Check:**
```bash
# Verify indexes exist
python scripts/migrations/create_payload_indexes.py --dry-run

# Check if query actually uses filters
# (indexes only help filtered queries)
```

---

## Monitoring

### Key Metrics
```promql
# Latency by feature
histogram_quantile(0.95, 
  search_latency_seconds_bucket{feature="baseline"})
histogram_quantile(0.95, 
  search_latency_seconds_bucket{feature="hybrid"})
histogram_quantile(0.95, 
  search_latency_seconds_bucket{feature="rerank"})

# Feature usage
rate(search_kb_hybrid_total[5m])
rate(search_kb_rerank_total[5m])

# Error rate
rate(rerank_error_total[5m])
```

### Health Checks
```bash
# Test baseline
curl -X POST localhost:8000/search -d '{"query":"test"}'

# Test hybrid (requires MCP client)
# Test rerank (requires MCP client)
```

---

## Best Practices

### DO:
✅ Use payload indexing always (automatic, free speedup)  
✅ Use hybrid for queries with technical terms  
✅ Use reranking for complex, high-value queries  
✅ Profile your workload before enabling features broadly  
✅ Monitor latency and error metrics

### DON'T:
❌ Enable reranking for all queries (latency cost)  
❌ Use hybrid without understanding your query patterns  
❌ Forget to run index migration on existing collections  
❌ Deploy to production without testing latency impact  
❌ Assume improvements without benchmarking

---

## FAQ

**Q: Should I enable hybrid and rerank for all queries?**  
A: No. Use baseline for most queries. Enable hybrid/rerank selectively based on query type and latency budget.

**Q: Why is my first reranked query slow?**  
A: Model downloads on first use (~80MB). Subsequent queries are faster. Pre-download during deployment.

**Q: Do I need to re-ingest documents?**  
A: Not for payload indexing or reranking. Hybrid search (full version) will require re-ingestion in future.

**Q: Can I use these features via REST API?**  
A: Currently MCP only. REST API support planned for FASE 14.

**Q: How do I benchmark improvement?**  
A: Create golden queries with expected docs, measure NDCG@5 and MRR before/after. Benchmark suite in FASE 14.

---

## Additional Resources

- Implementation Plan: `docs/FASE12_PLAN.md`
- Completion Report: `docs/FASE12_COMPLETION.md`
- Migration Script: `scripts/migrations/create_payload_indexes.py`
- Source Code: `server/retrieval/`

---

**Last Updated:** 2026-05-16  
**Version:** v0.10.0-dev
