# Kubernetes Deployment Guide

KB-RAG-MCP ships a Helm chart for deploying the full stack (kb-server, Qdrant,
optional Redis) on any Kubernetes cluster.

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| `kubectl` | 1.28 |
| `helm` | 3.12 |
| Kubernetes cluster | 1.28 (local: kind, k3s, Rancher Desktop) |

---

## Quick Start

```bash
# 1. Clone the repo (if not already done)
git clone https://github.com/your-org/kb-rag-mcp.git
cd kb-rag-mcp

# 2. Install with defaults (2 kb-server replicas, Qdrant StatefulSet, no Redis)
helm install kb-rag-mcp ./deployment/helm/kb-rag-mcp

# 3. Wait for all pods to be ready
kubectl rollout status deployment/kb-rag-mcp-kb-rag-mcp
kubectl rollout status statefulset/kb-rag-mcp-kb-rag-mcp-qdrant

# 4. Port-forward and test
kubectl port-forward svc/kb-rag-mcp-kb-rag-mcp 8000:8000 &
curl http://localhost:8000/health
```

---

## Configuration Reference

All settings live in `values.yaml`. Override at install time with `-f` or
`--set`:

```bash
helm install kb-rag-mcp ./deployment/helm/kb-rag-mcp \
  --set replicaCount=3 \
  --set config.qdrantCollection=my_kb \
  --set qdrant.persistence.size=100Gi
```

### Key values

| Key | Default | Description |
|---|---|---|
| `replicaCount` | `2` | Number of kb-server pods |
| `image.repository` | `kb-rag-mcp` | Container image |
| `image.tag` | `latest` | Image tag |
| `config.transport` | `sse` | MCP transport (`sse` or `stdio`) |
| `config.qdrantCollection` | `kb_docs` | Default Qdrant collection name |
| `config.logLevel` | `INFO` | Python log level |
| `autoscaling.enabled` | `true` | Enable HPA |
| `autoscaling.minReplicas` | `2` | HPA minimum pods |
| `autoscaling.maxReplicas` | `10` | HPA maximum pods |
| `autoscaling.targetCPUUtilizationPercentage` | `70` | CPU target for scale-out |
| `qdrant.enabled` | `true` | Deploy Qdrant as StatefulSet |
| `qdrant.image.tag` | `v1.9.0` | Qdrant image version |
| `qdrant.persistence.size` | `50Gi` | Qdrant PVC size |
| `qdrant.persistence.storageClass` | `standard` | PVC storage class |
| `redis.enabled` | `false` | Deploy Redis sidecar |
| `monitoring.enabled` | `true` | Enable /metrics endpoint |
| `monitoring.serviceMonitor.enabled` | `false` | Create Prometheus ServiceMonitor |
| `ingress.enabled` | `false` | Create Ingress resource |

---

## Multi-Collection Setup

FASE 15 adds multi-collection support. Each collection is an independent Qdrant
index — useful for separating knowledge domains (e.g., one per product, per
tenant, or per language).

### Creating a new collection

Use the `list_collections` MCP tool to see what exists, then ingest into a
named collection:

```bash
# Via MCP tool call (Claude Code / OpenCode)
list_collections()
# → kb_docs (default)

# Ingest to a new collection (auto-created on first ingest)
ingest_document(path="/docs/new-product", collection="new_product")

# Search in a specific collection
search_kb(query="install guide", collection="new_product")
```

### Deploying multiple collections

Multiple collections share one Qdrant instance. No Kubernetes changes are
required — just pass `collection=<name>` to MCP tools.

To pre-create collections at startup, set `config.qdrantCollection` to the
desired default and use the MCP `list_collections` / `ingest_document` tools
to populate other collections.

---

## Scaling

### Horizontal Pod Autoscaler

The HPA is enabled by default and scales kb-server pods based on CPU (target
70%) and memory (target 80%). Configure with:

```yaml
autoscaling:
  minReplicas: 2
  maxReplicas: 20
  targetCPUUtilizationPercentage: 60
```

### Resource tuning

For larger knowledge bases (>1M chunks):

```yaml
resources:
  requests:
    cpu: 1000m
    memory: 2Gi
  limits:
    cpu: 4000m
    memory: 8Gi

qdrant:
  persistence:
    size: 200Gi
  resources:
    limits:
      memory: 16Gi
```

---

## Monitoring

### Prometheus

KB-server exposes Prometheus metrics at `:8081/metrics`. With
`monitoring.serviceMonitor.enabled: true`, a `ServiceMonitor` CRD is created
for automatic scraping by the Prometheus Operator:

```yaml
monitoring:
  serviceMonitor:
    enabled: true
    namespace: monitoring
    interval: 15s
```

### Grafana

Import the pre-built dashboard from
`deployment/config/grafana-dashboard.json` (see `docs/OPERATIONS.md`).

Configure the data source to point at your in-cluster Prometheus:

```
http://prometheus-operated.monitoring.svc.cluster.local:9090
```

---

## Upgrading

```bash
# Pull latest image and upgrade
helm upgrade kb-rag-mcp ./deployment/helm/kb-rag-mcp \
  --set image.tag=1.1.0

# Dry-run first
helm upgrade kb-rag-mcp ./deployment/helm/kb-rag-mcp --dry-run
```

Qdrant data is preserved across upgrades because it lives on a PVC.

---

## Uninstall

```bash
helm uninstall kb-rag-mcp

# The PVC is NOT deleted automatically (Kubernetes default).
# To also delete Qdrant data:
kubectl delete pvc qdrant-data-kb-rag-mcp-kb-rag-mcp-qdrant-0
```

---

## Using an External Qdrant

To use an existing Qdrant instance instead of deploying one:

```yaml
qdrant:
  enabled: false   # don't deploy the StatefulSet
```

Then pass the host via extra env in your values override:

```yaml
# values-prod.yaml
qdrant:
  enabled: false

# extra env injected into the kb-server Deployment
extraEnv:
  - name: QDRANT_HOST
    value: qdrant.my-namespace.svc.cluster.local
  - name: QDRANT_PORT
    value: "6333"
```

---

## Helm Lint

Before deploying, validate the chart:

```bash
helm lint ./deployment/helm/kb-rag-mcp
```

Expected output: `1 chart(s) linted, 0 chart(s) failed`
