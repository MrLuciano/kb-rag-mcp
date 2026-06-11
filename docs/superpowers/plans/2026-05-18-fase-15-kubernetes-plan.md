# PHASE 15 — Kubernetes + Multi-Collection Plan

> **Status:** PLAN ONLY — Not yet implemented. Implement after all other PHASEs are complete.

**Goal:** Add Kubernetes deployment support (Helm chart) and multi-collection routing to serve different knowledge domains from a single cluster without index collision.

---

## Architecture Overview

### Multi-Collection Routing

Currently all documents share one Qdrant collection (`kb_docs`). PHASE 15 adds:

- `CollectionManager` — creates/lists/deletes collections; mirrors Qdrant API
- `CollectionRouter` — routes MCP tool calls to the correct collection based on `collection` parameter
- Backward compatibility: if no `collection` specified, routes to `QDRANT_COLLECTION` env var (default: `kb_docs`)

### Kubernetes Deployment

- Helm chart under `deployment/helm/kb-rag-mcp/`
- Components: kb-server (FastAPI), Qdrant (StatefulSet), Prometheus, Grafana, Redis (optional)
- HorizontalPodAutoscaler for kb-server
- PersistentVolumeClaim for Qdrant data

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `kb_server/collections/manager.py` | Create | CollectionManager — CRUD for Qdrant collections |
| `kb_server/collections/router.py` | Create | CollectionRouter — routes requests to correct collection |
| `kb_server/collections/__init__.py` | Create | Package marker |
| `kb_server/server.py` | Modify | Add `collection` param to search/ingest MCP tools |
| `docs/KUBERNETES.md` | Create | Kubernetes deployment guide |
| `deployment/helm/kb-rag-mcp/Chart.yaml` | Create | Helm chart metadata |
| `deployment/helm/kb-rag-mcp/values.yaml` | Create | Default values (replicas, resources, images) |
| `deployment/helm/kb-rag-mcp/templates/deployment.yaml` | Create | kb-server Deployment |
| `deployment/helm/kb-rag-mcp/templates/qdrant.yaml` | Create | Qdrant StatefulSet + PVC |
| `deployment/helm/kb-rag-mcp/templates/hpa.yaml` | Create | HorizontalPodAutoscaler |
| `deployment/helm/kb-rag-mcp/templates/service.yaml` | Create | Services |
| `deployment/helm/kb-rag-mcp/templates/configmap.yaml` | Create | Environment configmap |
| `tests/test_collection_manager.py` | Create | Unit tests for CollectionManager |
| `tests/test_collection_router.py` | Create | Unit tests for CollectionRouter |

---

## Task 1: CollectionManager

**Files:** `kb_server/collections/__init__.py`, `kb_server/collections/manager.py`, `tests/test_collection_manager.py`

### Design

```python
class CollectionManager:
    def __init__(self, qdrant_client):
        self.client = qdrant_client

    async def list_collections(self) -> list[str]:
        """Return names of all existing collections."""

    async def create_collection(self, name: str, vector_size: int = 1024) -> bool:
        """Create collection if not exists. Returns True if created, False if already existed."""

    async def delete_collection(self, name: str) -> bool:
        """Delete collection. Returns True if deleted."""

    async def collection_exists(self, name: str) -> bool:
        """Check if collection exists."""
```

### Tests

```python
# tests/test_collection_manager.py
# All tests use AsyncMock for qdrant_client
def test_list_collections_returns_names():
def test_create_collection_calls_qdrant():
def test_create_collection_skips_if_exists():
def test_delete_collection_calls_qdrant():
def test_collection_exists_true():
def test_collection_exists_false():
```

---

## Task 2: CollectionRouter

**Files:** `kb_server/collections/router.py`, `tests/test_collection_router.py`

### Design

```python
class CollectionRouter:
    def __init__(self, manager: CollectionManager, default_collection: str):
        self.manager = manager
        self.default = default_collection

    async def resolve(self, collection: str | None) -> str:
        """
        Returns effective collection name.
        If collection is None, returns self.default.
        If collection is specified but doesn't exist, raises CollectionNotFoundError.
        """

    async def ensure(self, collection: str | None) -> str:
        """
        Like resolve() but creates the collection if it doesn't exist.
        Used for ingest paths.
        """
```

### Tests

```python
# tests/test_collection_router.py
def test_resolve_none_returns_default():
def test_resolve_existing_returns_name():
def test_resolve_missing_raises_error():
def test_ensure_creates_if_missing():
def test_ensure_returns_existing():
```

---

## Task 3: Wire into server.py

Add optional `collection: str | None = None` parameter to MCP tool handlers:

- `search_kb(query, ..., collection=None)` — routes to resolved collection
- `ingest_document(path, ..., collection=None)` — routes to ensured collection
- `list_collections()` — new MCP tool listing all collections

Backward compatibility: all existing calls without `collection` continue to work unchanged.

---

## Task 4: Helm Chart

### Chart.yaml

```yaml
apiVersion: v2
name: kb-rag-mcp
description: KB-RAG-MCP — OpenText RAG Pipeline
type: application
version: 0.1.0
appVersion: "1.0"
```

### values.yaml (key defaults)

```yaml
replicaCount: 2

image:
  repository: kb-rag-mcp
  tag: latest
  pullPolicy: IfNotPresent

qdrant:
  enabled: true
  persistence:
    size: 50Gi
    storageClass: standard

redis:
  enabled: false

resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

---

## Task 5: KUBERNETES.md

Sections:
1. Prerequisites (kubectl, helm, cluster access)
2. Quick Start (`helm install kb-rag-mcp ./deployment/helm/kb-rag-mcp`)
3. Configuration Reference (all values.yaml keys)
4. Multi-Collection Setup (creating collections, routing)
5. Scaling (HPA, resource tuning)
6. Monitoring (Prometheus/Grafana integration)
7. Upgrading (`helm upgrade`)
8. Uninstall

---

## Dependencies

No new Python packages required. Kubernetes tooling:
- `helm >= 3.12` for chart management
- `kubectl >= 1.28` for cluster operations

---

## Constraints

- This PHASE is deliberately last — it depends on all other PHASEs being stable
- Helm chart should be validated with `helm lint` before merging
- Multi-collection must not break existing single-collection deployments
- `QDRANT_COLLECTION` env var remains the escape hatch for the default collection

---

## Implementation Notes

- `CollectionManager` wraps `qdrant_client.AsyncQdrantClient` — same client used in `VectorStore`
- Use `qdrant_client.models.VectorParams` for collection creation
- HNSW index params: `m=16`, `ef_construct=100` (same as existing collection)
- Payload indexes should be created on `product`, `doc_type`, `source` after collection creation
  (mirrors existing setup in `kb_server/vector_store.py`)
