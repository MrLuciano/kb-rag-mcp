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
kubectl port-forward svc/kb-rag-mcp-kb-rag-mcp 8080:8080 &
curl http://localhost:8080/health
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

Multi-collection support allows independent Qdrant indexes — useful for
separating knowledge domains (e.g., one per product, per tenant, or per
language).

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
    interval: 30s
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

> **CI Note:** `helm lint --strict` runs automatically on every push and PR
> via the project's CI pipeline, ensuring chart validity before merge.

---

## Ollama Embedding Backend (Optional)

KB-RAG-MCP supports deploying an Ollama instance as a local embedding backend.
This is useful for teams that prefer self-hosted embedding over external APIs.

### Model: nomic-embed-text v1.5

| Property | Value |
|----------|-------|
| **Parameters** | 137M |
| **Download size** | **274MB** (Q4_0 quantized) |
| **Dimensions** | 768 |
| **Context window** | 2,048 tokens |
| **Runtime memory** | ~1Gi (274MB weights + 500MB overhead) |
| **GPU** | Optional — works on CPU |
| **GPU memory if offloaded** | ~500MB (fits on any GPU with >1GB VRAM) |

### Enabling Ollama

```bash
# 1. Enable Ollama in Helm values
helm install kb-rag-mcp ./deployment/helm/kb-rag-mcp \
  --set ollama.enabled=true \
  --set ollama.model=nomic-embed-text:v1.5

# 2. Wait for model pull (init container handles this automatically)
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=ollama --timeout=300s

# 3. Verify
kubectl logs -l app.kubernetes.io/component=ollama
# → "Pull complete!"

# 4. Port-forward for testing
kubectl port-forward svc/kb-rag-mcp-ollama 11434:11434
```

### Helm Configuration

```yaml
# my-values.yaml
ollama:
  enabled: true
  model: "nomic-embed-text:v1.5"
  replicas: 1
  initPullModel: true
  image:
    repository: ollama/ollama
    tag: latest
  service:
    type: ClusterIP
    port: 11434
  persistence:
    enabled: true
    size: 5Gi
    storageClass: standard
  keepAlive: "24h"
  numParallel: 1
  maxLoadedModels: 1
  resources:
    requests:
      cpu: 250m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 2Gi
  # GPU acceleration (optional, not required for nomic-embed-text)
  gpu:
    enabled: false
    vendor: nvidia  # or "amd" for ROCm
    count: 1
```

### GPU Acceleration

For GPU-accelerated embedding (optional):

```yaml
ollama:
  gpu:
    enabled: true
    vendor: nvidia
    count: 1
  resources:
    requests:
      cpu: 250m
      memory: 1Gi
      nvidia.com/gpu: 1
    limits:
      cpu: 2000m
      memory: 2Gi
      nvidia.com/gpu: 1
```

### KB-RAG Integration

After deploying Ollama, configure KB-RAG to use it:

```yaml
extraEnv:
  - name: EMBED_BACKEND
    value: "ollama"
  - name: OLLAMA_HOST
    value: "http://kb-rag-mcp-ollama:11434"
  - name: EMBED_MODEL
    value: "nomic-embed-text:v1.5"
```

Or set via `--set`:

```bash
helm install kb-rag-mcp ./deployment/helm/kb-rag-mcp \
  --set ollama.enabled=true \
  --set extraEnv[0].name=EMBED_BACKEND \
  --set extraEnv[0].value=ollama \
  --set extraEnv[1].name=OLLAMA_HOST \
  --set extraEnv[1].value="http://kb-rag-mcp-ollama:11434" \
  --set extraEnv[2].name=EMBED_MODEL \
  --set extraEnv[2].value="nomic-embed-text:v1.5"
```

### Manual Model Pull

If `initPullModel` is disabled, pull the model manually:

```bash
# Forward to Ollama pod
kubectl port-forward svc/kb-rag-mcp-ollama 11434:11434 &

# Pull model
curl -X POST http://localhost:11434/api/pull \
  -d '{"name":"nomic-embed-text:v1.5"}'

# Verify
curl http://localhost:11434/api/tags
```

## v0.1.4 Environment Variables

When deploying v0.1.4 features, you may need to add these env vars:

```yaml
# values-v0.1.4.yaml
extraEnv:
  # Auth (Phase 32) — optional, default false
  - name: AUTH_ENABLED
    value: "true"
  - name: AUTH_DB_PATH
    value: "/data/auth.db"

  # Rate Limiting (Phase 33) — optional, default false
  - name: RATE_LIMIT_ENABLED
    value: "true"
  - name: RATE_LIMIT_REQUESTS
    value: "100"
  - name: RATE_LIMIT_WINDOW
    value: "60"

  # Circuit Breaker (Phase 36)
  - name: CIRCUIT_BREAKER_THRESHOLD
    value: "5"
  - name: CIRCUIT_BREAKER_COOLDOWN
    value: "30"

  # Retrieval Cache (Phase 37)
  - name: RETRIEVAL_CACHE_TTL
    value: "300"

  # Connectors (Phase 29) — uncomment if using enterprise sources
  # - name: CONFLUENCE_URL
  #   value: "https://confluence.example.com"
  # - name: CONFLUENCE_USERNAME
  #   value: "bot"
  # - name: CONFLUENCE_TOKEN
  #   valueFrom:
  #     secretKeyRef:
  #       name: confluence-credentials
  #       key: token
```

> **Note:** Auth, rate limiting, and circuit breaker are all OPTIONAL and OFF by default. Only configure them if you need those features. Connector credentials should be stored as Kubernetes Secrets, not in ConfigMaps.

---

*Last updated: 2026-06-29 for v0.1.5*
