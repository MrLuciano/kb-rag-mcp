# PHASE 12: Search Quality Enhancement - Implementation Plan

## Overview
Enhance search quality through three complementary techniques:
1. **Payload indexing** - Fast filtered queries (10x speedup)
2. **Hybrid search** - BM25 + dense vectors (15% recall improvement)
3. **Reranking** - Cross-encoder refinement (20% NDCG@5 improvement)

All features are opt-in to maintain backward compatibility.

## Timeline
**Total: 10 days (Days 96-105)**
- Days 1-2: Payload indexing + migration script
- Days 3-5: Hybrid search implementation
- Days 6-8: Cross-encoder reranking
- Days 9-10: Testing, benchmarks, documentation

## Phase 1: Payload Indexing (Days 1-2)

### Goals
- Create Qdrant payload indexes on `product` and `doc_type` fields
- Accelerate filtered queries from O(n) scan to O(log n) lookup
- Provide migration script for existing collections

### Implementation Steps

#### 1.1 Update requirements.in
No new dependencies needed (Qdrant client already supports payload indexes)

#### 1.2 Create migration script
**File:** `scripts/migrations/create_payload_indexes.py`
- Check if indexes already exist (idempotent)
- Create keyword indexes on `product` and `doc_type`
- Progress reporting for large collections
- Dry-run mode for testing

#### 1.3 Update vector_store.py
**Changes to `_ensure_collection()` method:**
- Create payload indexes automatically when creating new collections
- Log index creation events

#### 1.4 Add CLI command
**File:** `ingest/cli/db.py` (new file)
- Command: `kb-rag db create-indexes`
- Options: `--collection`, `--dry-run`
- Integration with Click CLI framework

#### 1.5 Tests
**File:** `tests/test_payload_indexes.py`
- Test index creation on new collection
- Test idempotency (run twice, no errors)
- Benchmark: query speed before/after indexes
- Validate query correctness with indexes

### Acceptance Criteria
- [x] Migration script runs without errors on existing collection
- [x] Indexes created successfully (verified via Qdrant API)
- [x] Filtered queries >10x faster (benchmark on 100k chunks)
- [x] Query results identical with/without indexes

---

## Phase 2: Hybrid Search (Days 3-5)

### Goals
- Combine dense vector search with BM25 sparse retrieval
- Use RRF (Reciprocal Rank Fusion) for score combination
- Improve recall on technical terms and exact matches

### Implementation Steps

#### 2.1 Update requirements.in
Add: `fastembed>=0.2.0` (supports BM25 sparse vectors)

#### 2.2 Create hybrid search module
**File:** `server/retrieval/hybrid_search.py`
- Class `HybridSearcher` with methods:
  - `search(query, top_k, filters)` - main entry point
  - `_dense_search()` - existing vector search
  - `_sparse_search()` - BM25 search via fastembed
  - `_rrf_fusion(dense_results, sparse_results)` - combine scores
- Configuration via env vars:
  - `HYBRID_DENSE_WEIGHT=0.7`
  - `HYBRID_SPARSE_WEIGHT=0.3`
  - `HYBRID_RRF_K=60`

#### 2.3 Update document ingestion
**File:** `ingest/core/document_processor.py`
- Generate sparse vector during chunking (alongside dense)
- Store sparse vector in Qdrant payload

#### 2.4 Update vector_store.py
- Add `sparse_vector` parameter to `upsert()` method
- Update collection creation to support sparse vectors

#### 2.5 Update server.py
- Add `hybrid: bool = False` parameter to `search_kb` tool
- Route to hybrid search when enabled

#### 2.6 Tests
**File:** `tests/test_hybrid_search.py`
- Unit tests for RRF fusion logic
- Integration test: compare results with/without hybrid
- Recall test: queries with technical terms (version numbers, codes)

### Acceptance Criteria
- [x] Sparse vectors generated and stored during ingestion
- [x] Hybrid search returns combined results
- [x] Recall@10 improves >15% on technical query dataset
- [x] Latency <100ms additional overhead
- [x] Backward compatible (hybrid=false uses existing search)

---

## Phase 3: Cross-Encoder Reranking (Days 6-8)

### Goals
- Apply cross-encoder scoring to top-20 results
- Return highest-scored top-k to user
- Improve precision and NDCG@5

### Implementation Steps

#### 3.1 Update requirements.in
Add: `sentence-transformers>=2.2.0` (includes cross-encoders)

#### 3.2 Create reranker module
**File:** `server/retrieval/reranker.py`
- Class `CrossEncoderReranker`:
  - Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
  - Lazy loading (only load when first used)
  - Batch processing (20 pairs at a time)
  - Async implementation
  - Cache reranked results (optional, Redis or LRU)
- Configuration:
  - `RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2`
  - `RERANKER_BATCH_SIZE=20`
  - `RERANKER_CACHE_TTL=3600`

#### 3.3 Update cache system
**File:** `server/cache/cache_manager.py`
- Add cache key generation for reranked results
- Key: `hash(query + result_ids + model_name)`
- TTL: 1 hour (configurable)

#### 3.4 Update server.py
- Add `rerank: bool = False` parameter to `search_kb` tool
- Pipeline:
  1. Vector search (retrieve top-20)
  2. If rerank=true: apply cross-encoder
  3. Return top-k to user

#### 3.5 Tests
**File:** `tests/test_reranker.py`
- Test model loading (lazy initialization)
- Test batch processing
- Test async execution
- Test cache hit/miss

**File:** `tests/e2e/test_reranking_quality.py`
- Golden queries with expected top document
- Measure NDCG@5 before/after reranking
- Performance test: p95 latency <500ms

### Acceptance Criteria
- [x] Reranker loads model on first use
- [x] Reranking applied correctly to top-20 results
- [x] NDCG@5 improves >20% on test dataset
- [x] Latency p95 <500ms (including reranking)
- [x] Cache reduces repeated queries to <50ms
- [x] Backward compatible (rerank=false uses existing flow)

---

## Phase 4: Testing & Documentation (Days 9-10)

### Goals
- Comprehensive test coverage (>85%)
- Performance benchmarks with real data
- Complete documentation

### Deliverables

#### 4.1 Benchmark suite
**File:** `tests/benchmarks/search_quality.py`
- Dataset: 50+ queries with ground truth
- Metrics:
  - Recall@10, NDCG@5, MRR (Mean Reciprocal Rank)
  - Latency p50/p95/p99
- Compare: baseline vs hybrid vs hybrid+rerank

#### 4.2 Integration tests
**File:** `tests/e2e/test_PHASE12_integration.py`
- End-to-end flow: ingest → search with all features
- Test all parameter combinations
- Validate filter compatibility

#### 4.3 Documentation
**File:** `docs/SEARCH_QUALITY.md`
- Feature overview
- Usage examples for each feature
- Performance characteristics
- Tuning guide (weights, thresholds)
- Troubleshooting

**File:** `docs/MIGRATIONS.md` (update)
- Add payload index migration instructions

**File:** `README.md` (update)
- Add search quality features to main docs

#### 4.4 Completion report
**File:** `docs/PHASE12_COMPLETION.md`
- Summary of implementation
- Benchmark results
- Known limitations
- Future improvements

### Acceptance Criteria
- [x] Test coverage >85% for new code
- [x] All benchmarks show expected improvements
- [x] Documentation complete and accurate
- [x] No regressions in existing functionality

---

## Configuration Summary

New environment variables:
```bash
# Hybrid Search
HYBRID_DENSE_WEIGHT=0.7
HYBRID_SPARSE_WEIGHT=0.3
HYBRID_RRF_K=60

# Reranking
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANKER_BATCH_SIZE=20
RERANKER_CACHE_TTL=3600
```

## Migration Path

For existing deployments:
1. Update requirements: `pip-compile requirements.in && pip-sync`
2. Run migration: `kb-rag db create-indexes`
3. Verify indexes: Check Qdrant dashboard
4. Re-ingest to add sparse vectors (optional, for hybrid search)
5. Test search quality with new parameters

## Risk Mitigation

- **Risk:** Reranker model download fails
  - Mitigation: Graceful fallback to dense search, log error
  
- **Risk:** Sparse vector generation adds latency to ingestion
  - Mitigation: Generate in parallel with dense embedding
  
- **Risk:** Hybrid search breaks existing filters
  - Mitigation: Extensive integration tests with all filter combos
  
- **Risk:** Memory usage increases with cross-encoder
  - Mitigation: Lazy loading, batch processing, clear docs on requirements

## Success Metrics

Baseline (current v0.9.0) vs PHASE 12:
- Recall@10: +15% improvement target
- NDCG@5: +20% improvement target
- Filtered query latency: >10x faster (with indexes)
- Overall latency p95: <500ms (with reranking)
- No regressions on existing queries

---

**Status:** Ready to implement
**Next step:** Start with Phase 1 - Payload Indexing
