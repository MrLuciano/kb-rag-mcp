# Example Provisioning Guide

Reference hardware suggestions for deploying kb-rag-mcp on virtualized
machines. Use these as starting points — real requirements depend on
corpus size, query rate, and whether reranking / hybrid search are
enabled.

---

## Background

### Components

| Component | Role | Notes |
|-----------|------|-------|
| **kb-rag-mcp** | MCP server + FastAPI health server | Python 3.11, asyncio |
| **Qdrant** | Vector database (Docker) | Stores chunks + embeddings |
| **Embedding backend** | Converts text → vectors | Ollama / LM Studio / OpenAI-compat |
| **Web UI** | Admin panel (optional) | Alpine.js + HTMX on FastAPI |
| **Grafana + Prometheus** | Monitoring (optional) | ~1.5 GB combined |
| **Cross-encoder** | Reranker (optional, lazy) | sentence-transformers, ~80 MB |
| **Ingest worker** | File extraction + chunking | Runs in kb-rag-mcp process |

### Model Sizes

| Model | Size | RAM | GPU Benefit |
|-------|------|-----|-------------|
| `nomic-embed-text:v1.5` | 274 MB | ~1 GB | Minimal — runs fine on CPU |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | 80 MB | ~500 MB | Only used when reranking |
| `Qdrant/bm25` (sparse) | ~50 MB | ~200 MB | CPU only, no GPU path |

### Key Parameters

- **Corpus growth**: Each 10,000 chunks ≈ 500 MB in Qdrant (with payloads)
- **Docker memory limits**: Configured in `docker-compose.yml`; double them
  for production
- **Embedding throughput**: Ollama with CPU serves ~5–15 req/s per core
- **Hybrid search**: Adds ~50–100 ms per query (BM25 sparse + RRF fusion)
- **Reranking**: Adds ~200–500 ms per query (cross-encoder on CPU)

---

## Small Team (10 users)

Light usage: a few queries per hour, one product documentation set.
Corpus: 5,000–20,000 chunks, < 2 GB.

### Without GPU — Core System

**Use case:** CLI‑only access via MCP (Claude Code, OpenCode, Copilot).
No Web UI, no monitoring.

| Resource | Recommended | Minimum Viable |
|----------|-------------|---------------|
| **vCPU** | 2 | 1 |
| **RAM** | 8 GB | 4 GB |
| **Disk** | 40 GB (SSD) | 20 GB |
| **GPU** | None | None |

**Suggested VMs:**

| Provider | SKU | Monthly (approx) |
|----------|-----|-------------------|
| AWS | `t3.medium` (2 vCPU, 4 GB) | $30 |
| Azure | `B2s` (2 vCPU, 4 GB) | $30 |
| GCP | `e2-small` (2 vCPU, 4 GB) | $25 |
| Hetzner | `CX22` (2 vCPU, 4 GB) | $7 |
| DigitalOcean | `s-2vcpu-4gb` (2 vCPU, 4 GB) | $24 |

**Deployment:**

```yaml
# docker-compose.yml — minimal core
services:
  qdrant:
    image: qdrant/qdrant:latest
    volumes: ["./qdrant_storage:/qdrant/storage"]
  kb-rag-mcp:
    build: .
    environment:
      EMBED_BACKEND: ollama
      OLLAMA_HOST: http://ollama:11434
    depends_on: [qdrant, ollama]
  ollama:
    image: ollama/ollama
    command: ["ollama", "run", "nomic-embed-text:v1.5"]
```

### Without GPU — Full System

Same usage but with Web UI + monitoring.

| Resource | Recommended |
|----------|-------------|
| **vCPU** | 4 |
| **RAM** | 16 GB |
| **Disk** | 60 GB (SSD) |
| **GPU** | None |

**Suggested VMs:**

| Provider | SKU | Monthly (approx) |
|----------|-----|-------------------|
| AWS | `t3.large` (2 vCPU, 8 GB) | $60 |
| Azure | `B4ms` (4 vCPU, 16 GB) | $70 |
| GCP | `e2-standard-4` (4 vCPU, 16 GB) | $75 |
| Hetzner | `CX42` (4 vCPU, 16 GB) | $18 |
| DigitalOcean | `s-4vcpu-8gb` (4 vCPU, 8 GB) | $48 |

### With GPU — Full System

GPU is overkill for 10 users but useful if you run the cross-encoder
reranker on every query or embed very large batches during ingestion.

| Resource | Recommended |
|----------|-------------|
| **vCPU** | 4 |
| **RAM** | 16 GB |
| **Disk** | 80 GB (SSD) |
| **GPU** | NVIDIA T4 / RTX 3060 (8 GB VRAM) |

**Suggested VMs:**

| Provider | SKU | Monthly (approx) |
|----------|-----|-------------------|
| AWS | `g4dn.xlarge` (4 vCPU, 16 GB, T4) | $200 |
| Azure | `NC4as_T4_v3` (4 vCPU, 16 GB, T4) | $220 |
| GCP | `g2-standard-4` (4 vCPU, 16 GB, L4) | $200 |
| Hetzner | `GEX44` (4 vCPU, 32 GB, RTX 4000) | $60 |
| RunPod | CPU: 4 vCPU, RAM: 16 GB, GPU: RTX 3090 | $40 |

---

## Medium Team (100 users)

Moderate usage: dozens of queries per hour, multiple product
documentation sets, scheduled ingestion. Corpus: 50,000–200,000 chunks,
< 10 GB.

### Without GPU — Full System

| Resource | Recommended |
|----------|-------------|
| **vCPU** | 8 |
| **RAM** | 32 GB |
| **Disk** | 150 GB (SSD) |
| **GPU** | None |

**Suggested VMs:**

| Provider | SKU | Monthly (approx) |
|----------|-----|-------------------|
| AWS | `t3.2xlarge` (8 vCPU, 32 GB) | $240 |
| Azure | `D8s_v5` (8 vCPU, 32 GB) | $280 |
| GCP | `e2-standard-8` (8 vCPU, 32 GB) | $240 |
| Hetzner | `CX62` (8 vCPU, 32 GB) | $60 |
| DigitalOcean | `s-8vcpu-32gb` (8 vCPU, 32 GB) | $192 |

### With GPU — Full System

GPU helps if you frequently re-embed large document batches (nightly
ingestion) or run the cross-encoder reranker on every search result.

| Resource | Recommended |
|----------|-------------|
| **vCPU** | 8 |
| **RAM** | 32 GB |
| **Disk** | 200 GB (SSD) |
| **GPU** | NVIDIA A10 / RTX 4090 (24 GB VRAM) |

**Suggested VMs:**

| Provider | SKU | Monthly (approx) |
|----------|-----|-------------------|
| AWS | `g5.2xlarge` (8 vCPU, 32 GB, A10G) | $550 |
| Azure | `NC6s_v3` (6 vCPU, 112 GB, V100) | $900 |
| GCP | `g2-standard-8` (8 vCPU, 32 GB, L4) | $500 |
| Hetzner | `GEX62` (8 vCPU, 64 GB, RTX 4000) | $105 |
| RunPod | CPU: 8 vCPU, RAM: 32 GB, GPU: RTX 4090 | $120 |

---

## Ingestion Guide by Scenario

### How Many Chunks Fit

| Corpus | Raw Docs | Chunks | Qdrant Storage |
|--------|----------|--------|----------------|
| Single product manual (100 pages) | 1 PDF | ~200 | ~10 MB |
| Medium knowledge base (1,000 pages) | 30–50 docs | ~5,000 | ~250 MB |
| Large enterprise wiki (10,000 pages) | 500 docs | ~50,000 | ~2.5 GB |
| Full product family (50,000 pages) | 2,500 docs | ~250,000 | ~12 GB |

### Embedding Time (CPU, 4 cores, Ollama)

| Chunks | Approx Time |
|--------|-------------|
| 1,000 | 2 minutes |
| 10,000 | 20 minutes |
| 100,000 | 3 hours |
| 500,000 | 15 hours |

With GPU (T4), divide by 4–6×.

---

## Provisioning Checklist

```text
□ Choose backend: Ollama (self-contained) / LM Studio (desktop) /
  OpenAI-compat (external API)
□ Decide core vs full: need Web UI + monitoring?
□ Pick VM from table above
□ Provision disk: at least 2× estimated Qdrant storage
□ Open ports: 8765 (MCP SSE), 8001 (Web UI), 6333 (Qdrant),
  8080 (health), 11434 (Ollama, internal only)
□ Configure swap: 2 GB minimum if RAM constrained
□ Set up Docker + docker compose
□ cp config/.env.lxc .env (or create from scratch)
□ docker compose up -d
□ Pull embedding model: docker compose exec ollama ollama pull \
  nomic-embed-text:v1.5
□ Ingest docs: docker compose exec kb-rag-mcp kb-ingest \
  --docs /path/to/docs
□ Verify: curl http://localhost:8080/health/detailed | jq
```

---

## Reference: Port Summary

| Port | Service | Access |
|------|---------|--------|
| 8765 | MCP SSE (main) | AI clients |
| 8001 | Web UI | Internal users |
| 8080 | Health / metrics | Monitoring |
| 6333 | Qdrant gRPC | Internal only |
| 6334 | Qdrant HTTP | Internal only |
| 11434 | Ollama | Internal only |
| 3000 | Grafana | Admin (optional) |
| 9090 | Prometheus | Admin (optional) |
