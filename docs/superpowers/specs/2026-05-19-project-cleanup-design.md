# Design: Project Cleanup & FEATURES.md

**Date:** 2026-05-19  
**Status:** Approved

---

## Goal

Remove all personal/environment-specific identifiers from the project and replace PHASE completion/plan archive files with a single canonical `FEATURES.md`. The result should be a project anyone can clone and use without seeing references to a specific person's hardware, employer, or local network.

---

## Scope

### Files to modify

| File | Changes |
|---|---|
| `.env` | Replace IP with `<LM_STUDIO_HOST>`, add embedding model comments |
| `config/.env.gaming` → `config/.env.local` | Rename file, replace all "gaming" references inside |
| `config/.env.proxmox` → `config/.env.lxc` | Rename file, replace all "proxmox" references inside |
| `config/mcp-clients.json` | Replace IP with `<LM_STUDIO_HOST>` |
| `kb_server/embed_client.py` | Replace IP, add recommended model comment block |
| `kb_server/server.py` | Replace any occurrence of `192.168.*` IP addresses |
| `server/embed_client.py` | Same as kb_server version |
| `server/server.py` | Replace any occurrence of `192.168.*` IP addresses |
| `server/evaluation/golden_dataset.json` | Replace all OpenText products with generic examples |
| `scripts/setup.sh` | Replace "gaming"/"proxmox" env file references |
| `README.md` | Terminology, IP, hardware spec, embedding recommendation |
| `README.pt-BR.md` | Same in Portuguese |
| `docs/INSTRUCTIONS.md` | Terminology, IP, hardware spec |
| `docs/INSTRUCTIONS.pt-BR.md` | Same in Portuguese |
| `docs/REFERENCE.md` | Terminology replacements |
| `docs/INDEX.md` | Add FEATURES.md entry |
| `docs/superpowers/plans/2026-05-16-qa-otcs.md` | Replace OpenText references |
| `docs/superpowers/specs/2026-05-16-qa-otcs-design.md` | Replace OpenText references |
| `tests/test_migration.py` | Replace any IP/hostname references |

### Files to create

| File | Description |
|---|---|
| `FEATURES.md` (root) | Single document covering all 16+ features, one `##` section each |

### Files to leave unchanged

| Path | Reason |
|---|---|
| `docs/archive/PHASE*` | Historical record — keep as-is |
| `CHANGELOG.md` | Historical record — PHASE naming is intentional there |
| `docs/superpowers/plans/` (other plans) | Internal planning artifacts |

---

## Terminology Replacement Map

| Find (case-insensitive) | Replace with |
|---|---|
| `gaming machine` | `local machine` |
| `Gaming Machine` | `Local Machine` |
| `gamming machine` | `local machine` |
| `gaming` (as env/profile label) | `local` |
| `.env.gaming` | `.env.local` |
| `Proxmox` / `proxmox` | `LXC Server` / `lxc-server` |
| `Proxmox LXC` | `LXC Server` |
| `.env.proxmox` | `.env.lxc` |
| `192.168.1.177` | `<LM_STUDIO_HOST>` |
| Any other `192.168.*` occurrence | `<LM_STUDIO_HOST>` |
| `AMD Ryzen 7 8845HS` | removed (replace line with generic "local machine") |
| `Radeon 780M` / `RDNA 3` / `Vulkan` (hardware-specific) | removed |
| `8845HS` | removed |
| `OpenText` | `(vendor)` or removed depending on context |
| `OTCS` / `otcs` | removed or replaced with `kb-rag` |
| `xECM`, `OTDS`, `ArchiveCenter`, `ContentSuite` | generic product names (see golden_dataset section) |

---

## golden_dataset.json Replacement

Replace the 10 OpenText-specific examples with 10 generic software product examples using these product names:

- `AppServer` — application server product
- `DataSync` — data synchronization product  
- `AdminPortal` — web administration UI

Maintain identical JSON structure: `query`, `expected_answer`, `expected_docs`, `metadata` (product, version, doc_type).  
Use version `3.2` (neutral, plausible).  
Cover doc_types: `install_guide`, `admin_guide`, `release_notes`, `overview`.  
Distribution: 4 entries for `AppServer`, 3 for `DataSync`, 3 for `AdminPortal`.

Note: `server/evaluation/golden_dataset.json` is the only copy — there is no duplicate under `kb_server/`.

---

## Embedding Model Comment Block

Add to `.env` and `kb_server/embed_client.py`:

```
# Recommended embedding models (via LM Studio or Ollama):
#   - nomic-embed-text v1.5  — balanced, multilingual, MIT license (768-dim)
#   - mxbai-embed-large-v1   — fast on CPU, MTEB top-10 (1024-dim)
#   - bge-m3                 — best quality, dense+sparse unified (1024-dim)
```

Keep `EMBED_MODEL` in `.env` pointing to whatever is currently configured — do not change the model name.

---

## FEATURES.md Structure

Location: repo root (`FEATURES.md`)

```markdown
# Features

Overview of all implemented features in kb-rag-mcp.

## Table of Contents
[one line per feature]

## Feature 1: Core Ingest Pipeline
## Feature 2: Job Management & Scheduler
## Feature 3: Worker Pool & Rate Limiter
## Feature 4: Observability & Progress Tracking
## Feature 5: Embedding Cache (LRU + Redis)
## Feature 6: CLI (Click + Rich)
## Feature 7: Document Validators
## Feature 8: Connection Pooling & Batch Optimization
## Feature 9: Production Hardening & Grafana Dashboard
## Feature 10: Security Documentation
## Feature 11: Legacy Format Parsers & ZIP Handler
## Feature 12: Hybrid Search (BM25 + Dense RRF)
## Feature 13: Ingestion Automation (File Watcher)
## Feature 14: Observability & Audit (Query Logger + Web UI)
## Feature 15: Multi-Collection Routing + Kubernetes
## Feature 16: RAG Evaluation Pipeline
```

Each section contains:
- One-paragraph description (what it does, why it exists)
- Key files (2–5 file paths with one-line descriptions)
- Status: ✅ Implemented
- Notable design decisions (1–3 bullets, only if non-obvious)

---

## docs/INDEX.md Update

Add `FEATURES.md` entry at the top of the file list with description "Complete feature reference — all 16 implemented features".

---

## Constraints

- No changes to `docs/archive/` — historical record
- No changes to `CHANGELOG.md` — historical record uses PHASE naming intentionally
- CLI interfaces, env variable names, and MCP tool names are **not** changed
- `kb_server/` module paths and Python imports are **not** changed
- Commit atomically per logical group (terminology, golden_dataset, FEATURES.md, docs)
