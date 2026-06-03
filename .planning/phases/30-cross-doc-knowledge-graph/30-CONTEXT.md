# Phase 30: Cross-Document Knowledge Graph

**Status:** Backlog (promoted from ROADMAP.md)
**Priority:** High
**Code:** GRAPH-01
**Competitive Reference:** [qdrant-loader](https://github.com/martin-papy/qdrant-loader) — cross-document knowledge graphs
**Promoted from:** `.planning/ROADMAP.md` Backlog (High Priority)

## Objective

Build a knowledge graph layer that analyzes relationships between indexed documents — similarity clustering, entity extraction, topic modeling. Enables discovery of related content beyond vector matching, providing a richer discovery experience.

## Expected Deliverables

- Knowledge graph data structure (nodes = documents, edges = relationships)
- Similarity clustering (group related documents by topic/theme)
- Entity extraction (named entities, key phrases across corpus)
- Topic modeling (LDA or similar for theme discovery)
- Graph query API (find related docs, explore paths)
- Optional visualization overlay in search results
- MCP tool: `get_related_documents(doc_id)` and `explore_topic(topic)`

## Key Design Decisions to Research

- **Storage:** Store graph as separate Qdrant collection or in existing chunk metadata?
- **Update strategy:** Rebuild on re-ingest or incremental (entity extraction is expensive)
- **Entity extraction:** Use embedding-based clustering or rule-basedNER? Cost vs quality tradeoff
- **Graph queries:** Traverse graph at query time or pre-compute relationship scores?
- **Visualization:** How to display graph context in search results without overwhelming?

## Implementation Scope

### Document Similarity
- Compute pairwise document similarity using chunk embeddings (average pooling)
- Store similarity scores as edges in graph
- Threshold-based clustering (e.g., cosine similarity > 0.85 = related)

### Entity Extraction
- Extract named entities (person, organization, product, location) across corpus
- Extract key phrases and technical terms
- Store as document metadata or separate entity collection

### Topic Modeling
- Apply LDA or similar to discover latent topics
- Map each document to topic distribution
- Store topic labels and weights in document metadata

### Graph Query API
- `get_related_documents(doc_id, depth=1)` — traverse graph
- `explore_topic(topic_id)` — get all docs in a topic cluster
- `find_entities(entity_name)` — find docs containing entity

## Open Questions

1. Real-time updates or batch recompute on schedule?
2. How to handle very large corpora (100K+ docs) — graph traversal costs?
3. Should graph data be per-KB or global across all KBs?

## See Also

- `qdrant-loader` knowledge graph implementation (GitHub: martin-papy/qdrant-loader)
- `kb_server/vector_store.py` — existing search infrastructure
- `kb_server/analytics/query_analyzer.py` — existing analytics patterns