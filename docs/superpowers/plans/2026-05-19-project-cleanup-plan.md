# Project Cleanup & FEATURES.md Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all personal/environment-specific identifiers (IP addresses, hardware specs, employer references) and produce a clean, generic, publicly shareable project — plus a single `FEATURES.md` documenting all 16 implemented features.

**Architecture:** Pure search-and-replace across documentation, config, and source files; rename two config files; rewrite golden_dataset.json with generic examples; create FEATURES.md from scratch. No functional code changes — no tests need to be written (no logic is touched).

**Tech Stack:** Python, Markdown, JSON, bash, git

---

## File Change Map

| File | Action | Change summary |
|---|---|---|
| `.env` | Modify | Replace IP, add model comments |
| `config/.env.gaming` | Rename + modify | → `config/.env.local`, update header + IP |
| `config/.env.proxmox` | Rename + modify | → `config/.env.lxc`, update header |
| `config/mcp-clients.json` | Modify | Replace "gaming"/"proxmox" keys and IPs |
| `kb_server/embed_client.py` | Modify | Replace IPs, "Proxmox" comment, add model comment block |
| `kb_server/server.py` | Modify | Remove "OpenText" from tool description string |
| `server/embed_client.py` | Modify | Same as kb_server version |
| `server/server.py` | Modify | Same as kb_server/server.py |
| `server/evaluation/golden_dataset.json` | Rewrite | Replace all 10 OpenText examples with generic ones |
| `scripts/setup.sh` | Modify | Replace "gaming"/"proxmox" profile names and references |
| `README.md` | Modify | All terminology, IPs, hardware specs |
| `README.pt-BR.md` | Modify | Same in Portuguese |
| `docs/INSTRUCTIONS.md` | Modify | All terminology, IPs, hardware specs, OpenText sections |
| `docs/INSTRUCTIONS.pt-BR.md` | Modify | Same in Portuguese |
| `docs/REFERENCE.md` | Modify | "OpenText", "OTCS" references |
| `docs/INDEX.md` | Modify | Add FEATURES.md entry |
| `docs/superpowers/plans/2026-05-16-qa-otcs.md` | Modify | Replace OTCS title/references |
| `docs/superpowers/specs/2026-05-16-qa-otcs-design.md` | Modify | Replace OTCS title/references |
| `tests/test_migration.py` | Modify | Replace hardcoded IP |
| `FEATURES.md` | Create | New root-level feature reference document |

---

### Task 1: Rename and update config env files

**Files:**
- Rename: `config/.env.gaming` → `config/.env.local`
- Rename: `config/.env.proxmox` → `config/.env.lxc`

- [ ] **Step 1: Rename the files**

```bash
git mv config/.env.gaming config/.env.local
git mv config/.env.proxmox config/.env.lxc
```

- [ ] **Step 2: Update `config/.env.local` header and contents**

Replace the file header (first 5 lines):
```
# ──────────────────────────────────────────────────────────────────────────────
# .env.local  —  Local Machine (Windows + WSL2 + LM Studio)
# ──────────────────────────────────────────────────────────────────────────────
# Embedding via LM Studio running on the local network
# EMBED_BACKEND recommended: openai-compat (pure HTTP, works remotely without SDK)
```

Replace the IP line:
```
LMS_BASE_URL=http://<LM_STUDIO_HOST>:1234
```

Add model comment block after `EMBED_MODEL=...`:
```bash
# Recommended embedding models (via LM Studio or Ollama):
#   - nomic-embed-text v1.5  — balanced, multilingual, MIT license (768-dim)
#   - mxbai-embed-large-v1   — fast on CPU, MTEB top-10 (1024-dim)
#   - bge-m3                 — best quality, dense+sparse unified (1024-dim)
```

- [ ] **Step 3: Update `config/.env.lxc` header**

Replace the file header (first 3 lines):
```
# ──────────────────────────────────────────────────────────────────────────────
# .env.lxc  —  LXC Server (CPU only, Ollama)
# ──────────────────────────────────────────────────────────────────────────────
```

- [ ] **Step 4: Commit**

```bash
git add config/.env.local config/.env.lxc
git commit -m "chore: rename .env.gaming→.env.local, .env.proxmox→.env.lxc; remove personal identifiers"
```

---

### Task 2: Update `.env` (root) and `config/mcp-clients.json`

**Files:**
- Modify: `.env`
- Modify: `config/mcp-clients.json`

- [ ] **Step 1: Update `.env` — replace IP, add model comments**

In `.env`, replace:
```
LMS_BASE_URL=http://192.168.1.177:1234
```
With:
```
LMS_BASE_URL=http://<LM_STUDIO_HOST>:1234
```

Add after the `EMBED_MODEL=...` line:
```bash
# Recommended embedding models (via LM Studio or Ollama):
#   - nomic-embed-text v1.5  — balanced, multilingual, MIT license (768-dim)
#   - mxbai-embed-large-v1   — fast on CPU, MTEB top-10 (1024-dim)
#   - bge-m3                 — best quality, dense+sparse unified (1024-dim)
```

Also replace the Portuguese comment on the Qdrant line:
```
# Qdrant running in Docker (local or WSL2)
```

- [ ] **Step 2: Update `config/mcp-clients.json`**

Apply these renames to JSON keys and string values:

| Old | New |
|---|---|
| `_claude_code_gaming_wsl2` | `_claude_code_local_wsl2` |
| `_opencode_gaming` | `_opencode_local` |
| `_claude_code_proxmox_ssh` | `_claude_code_lxc_ssh` |
| `_claude_code_proxmox_sse` | `_claude_code_lxc_sse` |
| `_opencode_proxmox_sse` | `_opencode_lxc_sse` |
| `"kb-proxmox"` | `"kb-lxc"` |
| `192.168.1.200` | `<LXC_SERVER_HOST>` |
| `"http://host.docker.internal:1234"` | `"http://<LM_STUDIO_HOST>:1234"` |

Update `_arquivo` descriptions:
- `"gaming"` → `"local"` in description strings

- [ ] **Step 3: Commit**

```bash
git add .env config/mcp-clients.json
git commit -m "chore: replace hardcoded IPs and personal env labels in .env and mcp-clients.json"
```

---

### Task 3: Update `kb_server/embed_client.py` and `server/embed_client.py`

**Files:**
- Modify: `kb_server/embed_client.py`
- Modify: `server/embed_client.py`

Both files are identical in content for the relevant sections.

- [ ] **Step 1: Update `kb_server/embed_client.py`**

Replace the docstring example lines (around line 13–15):
```python
  lmstudio-sdk:   LMS_HOST=<LM_STUDIO_HOST>  LMS_PORT=1234  (host only, no path)
  lmstudio-rest:  LMS_BASE_URL=http://<LM_STUDIO_HOST>:1234  (no /api or /v*)
  openai-compat:  LMS_BASE_URL=http://<LM_STUDIO_HOST>:1234  (no /v1)
```

Replace the example URL comment (around line 40):
```python
# e.g.: http://<LM_STUDIO_HOST>:1234/api/v1  →  http://<LM_STUDIO_HOST>:1234
```

Replace the Ollama docstring (around line 238):
```python
"""Ollama native — ideal for LXC Server / Linux without GPU."""
```

Replace the `- ollama` backend comment (around line 8):
```python
  - ollama         → Ollama native (recommended for LXC Server / Linux)
```

Add the model recommendation comment block after the backend list in the module docstring:
```python
# Recommended embedding models (via LM Studio or Ollama):
#   - nomic-embed-text v1.5  — balanced, multilingual, MIT license (768-dim)
#   - mxbai-embed-large-v1   — fast on CPU, MTEB top-10 (1024-dim)
#   - bge-m3                 — best quality, dense+sparse unified (1024-dim)
```

- [ ] **Step 2: Apply identical changes to `server/embed_client.py`**

Same replacements as Step 1.

- [ ] **Step 3: Verify no IP remains**

```bash
grep -n "192\.168\." kb_server/embed_client.py server/embed_client.py
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add kb_server/embed_client.py server/embed_client.py
git commit -m "chore: replace IPs and Proxmox references in embed_client.py; add model recommendations"
```

---

### Task 4: Update `kb_server/server.py`, `server/server.py`, and `tests/test_migration.py`

**Files:**
- Modify: `kb_server/server.py`
- Modify: `server/server.py`
- Modify: `tests/test_migration.py`

- [ ] **Step 1: Update `kb_server/server.py`**

Find the tool description string containing "OpenText" (around line 110) and replace with a generic description. Change:
```python
"de produtos OpenText e padrões técnicos. "
```
To:
```python
"de documentação técnica e padrões. "
```

- [ ] **Step 2: Apply identical change to `server/server.py`** (around line 106)

- [ ] **Step 3: Update `tests/test_migration.py`**

Find (around line 120):
```python
env_file.write_text("LMS_BASE_URL=http://192.168.1.177:1234\nQDRANT_COLLECTION=kb_docs\n")
```
Replace with:
```python
env_file.write_text("LMS_BASE_URL=http://<LM_STUDIO_HOST>:1234\nQDRANT_COLLECTION=kb_docs\n")
```

- [ ] **Step 4: Run migration tests to confirm no breakage**

```bash
python -m pytest tests/test_migration.py -v 2>&1 | tail -20
```

Expected: all previously passing tests still pass (test reads the string — it does not validate the URL format).

- [ ] **Step 5: Commit**

```bash
git add kb_server/server.py server/server.py tests/test_migration.py
git commit -m "chore: remove OpenText reference from server tool description; replace IP in test fixture"
```

---

### Task 5: Update `scripts/setup.sh`

**Files:**
- Modify: `scripts/setup.sh`

- [ ] **Step 1: Update profile names and comments**

Replace usage comment (around line 7–8):
```bash
#   bash scripts/setup.sh local    # local machine (WSL2 + LM Studio)
#   bash scripts/setup.sh lxc      # LXC Server (Ollama)
```

Replace default profile (around line 12):
```bash
PROFILE="${1:-local}"
```

Replace profile conditionals (around lines 31 and 40):
```bash
if [ "$PROFILE" = "lxc" ]; then
```
```bash
elif [ "$PROFILE" = "local" ]; then
```

Replace any inline comments mentioning "Proxmox" or "gaming":
- `# Proxmox LXC` → `# LXC Server`
- `# gaming machine` → `# local machine`

- [ ] **Step 2: Verify the script still executes without errors (dry-run)**

```bash
bash -n scripts/setup.sh
```

Expected: no syntax errors.

- [ ] **Step 3: Commit**

```bash
git add scripts/setup.sh
git commit -m "chore: rename setup.sh profiles gaming→local, proxmox→lxc"
```

---

### Task 6: Rewrite `server/evaluation/golden_dataset.json`

**Files:**
- Rewrite: `server/evaluation/golden_dataset.json`

- [ ] **Step 1: Replace entire file contents**

Write the following JSON (10 entries; 4 AppServer, 3 DataSync, 3 AdminPortal):

```json
[
  {
    "query": "How to install AppServer on Linux?",
    "expected_answer": "Install prerequisites (Java 17+, PostgreSQL 14+), extract archive to /opt/appserver, run install.sh, configure database connection in config/db.properties, then start with systemctl start appserver.",
    "expected_docs": ["AppServer_3.2_Install_Guide.pdf"],
    "metadata": {
      "product": "AppServer",
      "version": "3.2",
      "doc_type": "install_guide"
    }
  },
  {
    "query": "What are the minimum hardware requirements for AppServer?",
    "expected_answer": "Minimum: 4 CPU cores, 8 GB RAM, 100 GB disk. Recommended: 8+ cores, 16 GB RAM, 500 GB SSD.",
    "expected_docs": ["AppServer_3.2_System_Requirements.pdf"],
    "metadata": {
      "product": "AppServer",
      "version": "3.2",
      "doc_type": "overview"
    }
  },
  {
    "query": "How to configure SSL for AppServer?",
    "expected_answer": "Generate a keystore with keytool, update server.xml with an SSL connector pointing to the keystore file, set keystorePass, and restart the service.",
    "expected_docs": ["AppServer_3.2_Admin_Guide.pdf"],
    "metadata": {
      "product": "AppServer",
      "version": "3.2",
      "doc_type": "admin_guide"
    }
  },
  {
    "query": "How to perform a silent installation of AppServer?",
    "expected_answer": "Create a response file (response.properties) with all required parameters, then run: ./install.sh --silent --response-file response.properties",
    "expected_docs": ["AppServer_3.2_Install_Guide.pdf"],
    "metadata": {
      "product": "AppServer",
      "version": "3.2",
      "doc_type": "install_guide"
    }
  },
  {
    "query": "How to configure DataSync connection pools?",
    "expected_answer": "In datasync.properties, set pool.min=5, pool.max=50, pool.timeout=30000. Restart the DataSync service after changes.",
    "expected_docs": ["DataSync_3.2_Admin_Guide.pdf"],
    "metadata": {
      "product": "DataSync",
      "version": "3.2",
      "doc_type": "admin_guide"
    }
  },
  {
    "query": "What database versions does DataSync 3.2 support?",
    "expected_answer": "DataSync 3.2 supports PostgreSQL 13–15, MySQL 8.0, Oracle 19c and 21c, and Microsoft SQL Server 2019 and 2022.",
    "expected_docs": ["DataSync_3.2_Release_Notes.pdf"],
    "metadata": {
      "product": "DataSync",
      "version": "3.2",
      "doc_type": "release_notes"
    }
  },
  {
    "query": "How to enable debug logging in DataSync?",
    "expected_answer": "In datasync-logging.xml, set the root logger level to DEBUG. For component-level logging, add a logger entry: <logger name='com.example.datasync' level='DEBUG'/>. Restart to apply.",
    "expected_docs": ["DataSync_3.2_Admin_Guide.pdf"],
    "metadata": {
      "product": "DataSync",
      "version": "3.2",
      "doc_type": "admin_guide"
    }
  },
  {
    "query": "How to create a new admin user in AdminPortal?",
    "expected_answer": "Navigate to Settings > User Management > Users, click 'Add User', fill in the required fields, assign the 'admin' role, and click Save.",
    "expected_docs": ["AdminPortal_3.2_User_Guide.pdf"],
    "metadata": {
      "product": "AdminPortal",
      "version": "3.2",
      "doc_type": "admin_guide"
    }
  },
  {
    "query": "What is the default port for the AdminPortal web interface?",
    "expected_answer": "AdminPortal listens on port 8080 by default. To change it, update the 'server.port' property in application.properties and restart the service.",
    "expected_docs": ["AdminPortal_3.2_Install_Guide.pdf"],
    "metadata": {
      "product": "AdminPortal",
      "version": "3.2",
      "doc_type": "install_guide"
    }
  },
  {
    "query": "How to back up AdminPortal configuration?",
    "expected_answer": "Run the built-in export tool: ./adminportal-cli.sh export-config --output /backup/adminportal-config-$(date +%Y%m%d).zip. Schedule with cron for automated backups.",
    "expected_docs": ["AdminPortal_3.2_Admin_Guide.pdf"],
    "metadata": {
      "product": "AdminPortal",
      "version": "3.2",
      "doc_type": "admin_guide"
    }
  }
]
```

- [ ] **Step 2: Commit**

```bash
git add server/evaluation/golden_dataset.json
git commit -m "chore: replace OpenText-specific golden_dataset with generic AppServer/DataSync/AdminPortal examples"
```

---

### Task 7: Update `README.md` and `README.pt-BR.md`

**Files:**
- Modify: `README.md`
- Modify: `README.pt-BR.md`

Apply these replacements throughout both files:

| Find | Replace |
|---|---|
| `Gaming Machine` | `Local Machine` |
| `gaming machine` | `local machine` |
| `gaming` (as profile/label) | `local` |
| `Proxmox LXC` | `LXC Server` |
| `Proxmox` | `LXC Server` |
| `proxmox` (as profile/label) | `lxc` |
| `192.168.1.177` | `<LM_STUDIO_HOST>` |
| `192.168.1.200` | `<LXC_SERVER_HOST>` |
| `AMD Ryzen 7 8845HS` | `local CPU` |
| `Radeon 780M` | removed (delete the GPU spec line or replace with "iGPU") |
| `RDNA 3` | removed |
| `8845HS` | removed |
| `.env.gaming` | `.env.local` |
| `.env.proxmox` | `.env.lxc` |
| `config/mcp-clients.json → gaming block` | `config/mcp-clients.json → local block` |
| `config/mcp-clients.json → bloco gaming` | `config/mcp-clients.json → bloco local` |
| `setup.sh gaming` | `setup.sh local` |
| `setup.sh proxmox` | `setup.sh lxc` |
| Hardware spec table row with `8845HS` | Replace hardware column with `Local Machine` |

- [ ] **Step 1: Apply replacements to `README.md`**

Go through the file top-to-bottom applying all replacements in the table above.

- [ ] **Step 2: Verify no personal identifiers remain**

```bash
grep -n "192\.168\.\|Gaming\|gaming\|Proxmox\|proxmox\|Ryzen\|8845\|RDNA\|Radeon 780" README.md
```

Expected: no output.

- [ ] **Step 3: Apply same replacements to `README.pt-BR.md`**

- [ ] **Step 4: Verify `README.pt-BR.md`**

```bash
grep -n "192\.168\.\|Gaming\|gaming\|Proxmox\|proxmox\|Ryzen\|8845\|RDNA\|Radeon 780" README.pt-BR.md
```

Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add README.md README.pt-BR.md
git commit -m "chore: remove personal identifiers from README — IPs, hardware specs, env profile names"
```

---

### Task 8: Update `docs/INSTRUCTIONS.md` and `docs/INSTRUCTIONS.pt-BR.md`

**Files:**
- Modify: `docs/INSTRUCTIONS.md`
- Modify: `docs/INSTRUCTIONS.pt-BR.md`

Apply all replacements from Task 7's table, plus:

| Find | Replace |
|---|---|
| `Gaming Machine (primária)` | `Local Machine (primary)` |
| `Gaming Machine (Primária)` | `Local Machine (Primary)` |
| `Proxmox LXC (secundário / always-on)` | `LXC Server (secondary / always-on)` |
| `Proxmox LXC (Secundária / Always-On)` | `LXC Server (Secondary / Always-On)` |
| `Claude Code — Gaming Machine` | `Claude Code — Local Machine` |
| `Claude Code — Proxmox` | `Claude Code — LXC Server` |
| Hardware spec block (Ryzen/RAM/GPU) | Replace with: `- **Hardware:** Local machine with GPU or iGPU` |
| `lmstudio>=1.0.0 (gaming machine)` | `lmstudio>=1.0.0 (local machine with LM Studio)` |
| `# ollama>=0.2.0 # proxmox` | `# ollama>=0.2.0 # lxc server` |
| `bash scripts/setup.sh gaming` | `bash scripts/setup.sh local` |
| `bash scripts/setup.sh proxmox` | `bash scripts/setup.sh lxc` |
| `# Gaming machine — autostart` | `# Local machine — autostart` |
| `# Proxmox — systemd` | `# LXC Server — systemd` |
| OpenText product section (lines mentioning "OpenText ECM/EIM", OTCS, OTDS, xECM, ArchiveCenter) | Replace with a generic description: "The KB can contain any technical documentation. Product names and document types are classified automatically via metadata." |
| `de ~7 GB de documentação técnica de produtos OpenText` | `de documentação técnica e manuais de produtos` |
| `de ~7 GB+ de documentação técnica de produtos (OpenText ECM/EIM)` | `de documentação técnica e manuais de produtos` |

- [ ] **Step 1: Apply all replacements to `docs/INSTRUCTIONS.md`**

- [ ] **Step 2: Verify**

```bash
grep -n "192\.168\.\|Gaming\|gaming\|Proxmox\|proxmox\|Ryzen\|8845\|OpenText\|OTCS\|xECM\|OTDS\|ArchiveCenter\|ContentSuite" docs/INSTRUCTIONS.md
```

Expected: no output.

- [ ] **Step 3: Apply all replacements to `docs/INSTRUCTIONS.pt-BR.md`**

- [ ] **Step 4: Verify**

```bash
grep -n "192\.168\.\|Gaming\|gaming\|Proxmox\|proxmox\|Ryzen\|8845\|OpenText\|OTCS\|xECM\|OTDS\|ArchiveCenter\|ContentSuite" docs/INSTRUCTIONS.pt-BR.md
```

Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add docs/INSTRUCTIONS.md docs/INSTRUCTIONS.pt-BR.md
git commit -m "chore: remove personal identifiers and OpenText references from INSTRUCTIONS docs"
```

---

### Task 9: Update `docs/REFERENCE.md` and superpowers plan/spec files

**Files:**
- Modify: `docs/REFERENCE.md`
- Modify: `docs/superpowers/plans/2026-05-16-qa-otcs.md`
- Modify: `docs/superpowers/specs/2026-05-16-qa-otcs-design.md`

- [ ] **Step 1: Update `docs/REFERENCE.md`**

Find (around line 11):
```
that ingests OpenText product documentation, stores it as vector embeddings
```
Replace with:
```
that ingests technical documentation, stores it as vector embeddings
```

Find section heading (around line 305):
```
## QA Results (OTCS Corpus)
```
Replace with:
```
## QA Results
```

Find the QA run command (around line 322):
```
PYTHONPATH=. python -m qa.run_qa --eval --output ./QA_REPORT_OTCS.md
```
Replace with:
```
PYTHONPATH=. python -m qa.run_qa --eval --output ./QA_REPORT.md
```

Find the roadmap table entry (around line 384):
```
| QA | OTCS QA Pipeline | ✅ Complete | End-to-end eval, Hit Rate 100%, MRR 0.78 |
```
Replace with:
```
| QA | QA Evaluation Pipeline | ✅ Complete | End-to-end eval, Hit Rate 100%, MRR 0.78 |
```

- [ ] **Step 2: Update `docs/superpowers/plans/2026-05-16-qa-otcs.md`**

Replace the title line and any occurrence of "OTCS" or "OpenText":
- Title: Replace `qa-otcs` / `OTCS` references with `QA Evaluation Pipeline`
- Any OpenText product names → generic equivalents (AppServer, DataSync, AdminPortal)

- [ ] **Step 3: Update `docs/superpowers/specs/2026-05-16-qa-otcs-design.md`**

Same substitutions as Step 2.

- [ ] **Step 4: Verify REFERENCE.md**

```bash
grep -n "OpenText\|OTCS\|xECM\|OTDS" docs/REFERENCE.md
```

Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add docs/REFERENCE.md docs/superpowers/plans/2026-05-16-qa-otcs.md docs/superpowers/specs/2026-05-16-qa-otcs-design.md
git commit -m "chore: remove OpenText/OTCS references from REFERENCE.md and superpowers plan/spec"
```

---

### Task 10: Create `FEATURES.md`

**Files:**
- Create: `FEATURES.md` (repo root)

- [ ] **Step 1: Create the file with all 16 features**

Write `FEATURES.md` at the repo root with this content:

````markdown
# Features

Complete reference of all implemented features in **kb-rag-mcp**.

---

## Table of Contents

1. [Core Ingest Pipeline](#1-core-ingest-pipeline)
2. [Job Management & Scheduler](#2-job-management--scheduler)
3. [Worker Pool & Rate Limiter](#3-worker-pool--rate-limiter)
4. [Observability & Progress Tracking](#4-observability--progress-tracking)
5. [Embedding Cache (LRU + Redis)](#5-embedding-cache-lru--redis)
6. [CLI (Click + Rich)](#6-cli-click--rich)
7. [Document Validators](#7-document-validators)
8. [Connection Pooling & Batch Optimization](#8-connection-pooling--batch-optimization)
9. [Production Hardening & Grafana Dashboard](#9-production-hardening--grafana-dashboard)
10. [Security Documentation](#10-security-documentation)
11. [Legacy Format Parsers & ZIP Handler](#11-legacy-format-parsers--zip-handler)
12. [Hybrid Search (BM25 + Dense RRF)](#12-hybrid-search-bm25--dense-rrf)
13. [Ingestion Automation (File Watcher)](#13-ingestion-automation-file-watcher)
14. [Observability & Audit (Query Logger + Web UI)](#14-observability--audit-query-logger--web-ui)
15. [Multi-Collection Routing + Kubernetes](#15-multi-collection-routing--kubernetes)
16. [RAG Evaluation Pipeline](#16-rag-evaluation-pipeline)

---

## 1. Core Ingest Pipeline

Ingests documents (PDF, DOCX, TXT, MD, HTML) into a Qdrant vector store via chunking, classification, and embedding. The pipeline avoids re-ingesting unchanged files using a SQLite registry.

**Key files:**
- `ingest/ingest.py` — main CLI entrypoint; orchestrates extraction, chunking, embedding
- `ingest/classifier.py` — infers `product` and `doc_type` from filename/path via regex
- `ingest/registry.py` — SQLite-backed deduplication; tracks file hash and ingestion state
- `kb_server/vector_store.py` — Qdrant wrapper: upsert, search, list, stats

**Status:** ✅ Implemented

---

## 2. Job Management & Scheduler

Tracks each file as a `Job` with priority, status, and retry logic. A scheduler processes the queue in priority order, enabling visibility and control over long ingest runs.

**Key files:**
- `ingest/job/models.py` — `Job`, `JobStatus`, `JobPriority` dataclasses
- `ingest/job/manager.py` — `JobManager`: CRUD + lifecycle transitions
- `ingest/job/scheduler.py` — priority-based job dispatcher

**Status:** ✅ Implemented

---

## 3. Worker Pool & Rate Limiter

Async worker pool that processes jobs concurrently. A token-bucket rate limiter prevents overloading the embedding backend (LM Studio or Ollama).

**Key files:**
- `ingest/worker/pool.py` — `WorkerPool`: manages N async workers
- `ingest/worker/worker.py` — `FileWorker`: processes a single job with retry logic
- `ingest/worker/limiter.py` — token-bucket rate limiter
- `ingest/worker/executor.py` — `JobExecutor`: wires scheduler + pool together

**Status:** ✅ Implemented

---

## 4. Observability & Progress Tracking

Structured JSON logging and a 28-metric Prometheus exporter (`kb_*` prefix). Progress bars with ETA for long ingest runs.

**Key files:**
- `observability/logging.py` — structured JSON log formatter
- `observability/metrics.py` — 28 Prometheus counters/histograms/gauges
- `observability/progress.py` — progress tracking with ETA calculation

**Status:** ✅ Implemented

---

## 5. Embedding Cache (LRU + Redis)

In-memory LRU cache that deduplicates embedding calls for repeated or similar queries. Optional Redis backend for cross-process caching. RAM auto-tunes at startup.

**Key files:**
- `kb_server/cache/lru.py` — LRU cache with configurable RAM limit
- `kb_server/cache/redis.py` — optional Redis backend
- `kb_server/cache/manager.py` — unified interface; falls back to LRU if Redis unavailable

**Status:** ✅ Implemented

**Design note:** RAM limit is auto-detected at startup from available system memory. Redis connection failure is non-fatal — the cache degrades gracefully to in-memory LRU.

---

## 6. CLI (Click + Rich)

Full-featured command-line interface using Click for argument parsing and Rich for formatted output. Backward-compatible with the original positional-argument interface.

**Key files:**
- `ingest/cli/main.py` — top-level Click group
- `ingest/cli/job.py` — `ingest`, `status`, `retry`, `cancel` subcommands
- `ingest/cli/progress.py` — Rich progress bars and status tables
- `ingest/cli/legacy.py` — compatibility shim for old positional interface

**Status:** ✅ Implemented

---

## 7. Document Validators

Pre-ingest validation pipeline that checks format, file size, and content quality before queuing. Invalid files are logged and skipped without crashing the pipeline.

**Key files:**
- `ingest/validation/format.py` — extension and MIME type checks
- `ingest/validation/size.py` — file size limits (configurable per type)
- `ingest/validation/content.py` — minimum word count, encoding detection
- `ingest/validation/pipeline.py` — chains validators; returns structured result

**Status:** ✅ Implemented

---

## 8. Connection Pooling & Batch Optimization

Qdrant client uses a connection pool to avoid per-request overhead. Embeddings are batched in configurable chunks (default 32) to maximise throughput without exceeding backend limits.

**Key files:**
- `kb_server/vector_store.py` — batch upsert logic, pool configuration
- `kb_server/embed_client.py` — batched embedding calls with configurable batch size

**Status:** ✅ Implemented

---

## 9. Production Hardening & Grafana Dashboard

Health check endpoints, systemd service units, and a 18-panel Grafana dashboard for real-time monitoring.

**Key files:**
- `deployment/config/grafana-dashboard.json` — 18-panel dashboard (ingestion, workers, cache, latency)
- `deployment/config/grafana-provisioning/` — datasource + dashboard YAML for auto-provisioning
- `deployment/systemd/` — systemd unit files for bare-metal deployment
- `scripts/health_check.py` — end-to-end health check: embedding → Qdrant → search

**Status:** ✅ Implemented

---

## 10. Security Documentation

Threat model, attack surface analysis, and hardening guide for production deployment.

**Key files:**
- `docs/SECURITY.md` — threat model, hardening checklist, known limitations

**Status:** ✅ Implemented

---

## 11. Legacy Format Parsers & ZIP Handler

Extractors for legacy office formats and recursive ZIP unpacking, wired into the main ingest pipeline.

**Supported formats:** `.doc`, `.xls`, `.ppt`, `.odt`, `.ods`, `.odp`, `.wpd`, `.zip`

**Key files:**
- `ingest/parsers/legacy_office.py` — extractors with fallback chain: python-docx → antiword → LibreOffice CLI
- `ingest/parsers/zip_handler.py` — recursive ZIP extraction up to 2 levels, 500 MB/entry limit

**Status:** ✅ Implemented

---

## 12. Hybrid Search (BM25 + Dense RRF)

Combines dense vector search with BM25 sparse retrieval using Reciprocal Rank Fusion (RRF). Optionally re-ranks top-20 results with a cross-encoder.

**Key files:**
- `kb_server/retrieval/hybrid_search.py` — dense + sparse fusion with RRF
- `kb_server/retrieval/reranker.py` — cross-encoder re-ranking (model: `cross-encoder/ms-marco-MiniLM-L-6-v2`)

**Status:** ✅ Implemented

---

## 13. Ingestion Automation (File Watcher)

`watchdog`-based file watcher that monitors a directory and automatically queues new or modified files for ingestion.

**Key files:**
- `ingest/watcher/file_watcher.py` — `FileWatcher`: monitors path, debounces events, enqueues jobs

**Status:** ✅ Implemented

---

## 14. Observability & Audit (Query Logger + Web UI)

Every search query is logged to SQLite with 12 fields (query, filters, results, scores, latency). A FastAPI + HTMX web UI provides document browsing, search testing, and metadata inspection.

**Key files:**
- `kb_server/telemetry/query_logger.py` — SQLite query log, 90-day auto-rotation, <5 ms overhead
- `kb_server/ui/` — FastAPI + Bootstrap 5 + HTMX web interface (port 8001)
- `ingest/cli/export.py` — export document registry to JSON or CSV

**Status:** ✅ Implemented

**Design note:** Query logging is non-blocking. The web UI has no authentication (internal use only).

---

## 15. Multi-Collection Routing + Kubernetes

Routes MCP tool calls to named Qdrant collections. Collections can be created on demand or resolved strictly. Ships with a Helm chart for Kubernetes deployment.

**Key files:**
- `kb_server/collections/manager.py` — `CollectionManager`: list/create/delete/exists
- `kb_server/collections/router.py` — `CollectionRouter`: `resolve()` (strict) and `ensure()` (auto-create)
- `kb_server/server.py` — `collection=` parameter on `search_kb`, `list_documents`; `list_collections` tool
- `deployment/helm/kb-rag-mcp/` — Helm chart: Deployment, StatefulSet (Qdrant + PVC), HPA, Services, ConfigMap

**Status:** ✅ Implemented

**Design note:** `collection=` is optional — omitting it routes to `QDRANT_COLLECTION` (default: `kb_docs`), preserving backward compatibility.

---

## 16. RAG Evaluation Pipeline

End-to-end evaluation: query log analysis, a versioned golden dataset, RAGAS metrics (precision, recall, faithfulness), and chunk/score optimization experiment stubs.

**Key files:**
- `qa/run_qa.py` — QA pipeline entrypoint; runs eval against `queries.json`
- `qa/metrics.py` — Hit Rate, MRR, p50_score
- `server/analytics/query_analyzer.py` — analyzes query logs for low-score and zero-result patterns
- `server/evaluation/golden_dataset.json` — 10 hand-curated evaluation examples
- `server/evaluation/ragas_pipeline.py` — RAGAS evaluator stub (LLM integration optional)

**Status:** ✅ Implemented
````

- [ ] **Step 2: Commit**

```bash
git add FEATURES.md
git commit -m "docs: add FEATURES.md — single reference for all 16 implemented features"
```

---

### Task 11: Update `docs/INDEX.md` and final verification

**Files:**
- Modify: `docs/INDEX.md`

- [ ] **Step 1: Add `FEATURES.md` entry to `docs/INDEX.md`**

At the top of the document list, add:

```markdown
| [FEATURES.md](../FEATURES.md) | Complete feature reference — all 16 implemented features |
```

- [ ] **Step 2: Full project scan — confirm no personal identifiers remain**

```bash
grep -rn "192\.168\.\|Gaming\|gaming\|Proxmox\|proxmox\|Ryzen\|8845\|RDNA\|OpenText\|OTCS\|xECM\|OTDS\|ArchiveCenter\|ContentSuite" \
  --include="*.md" --include="*.py" --include="*.sh" --include="*.json" --include="*.yaml" --include="*.env*" \
  --exclude-dir=.venv --exclude-dir=.worktrees --exclude-dir=docs/archive \
  . 2>/dev/null | grep -v "CHANGELOG.md\|superpowers/plans\|superpowers/specs\|2026-05"
```

Expected: no output (CHANGELOG and archive are excluded intentionally).

- [ ] **Step 3: Run the full test suite to confirm nothing is broken**

```bash
python -m pytest tests/ -x --ignore=tests/e2e -q 2>&1 | tail -20
```

Expected: same pass/fail ratio as baseline (268 passing, 19 pre-existing failures).

- [ ] **Step 4: Commit INDEX update**

```bash
git add docs/INDEX.md
git commit -m "docs: add FEATURES.md to INDEX.md"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by |
|---|---|
| Replace IP `192.168.x.x` with `<LM_STUDIO_HOST>` / `<LXC_SERVER_HOST>` | Tasks 1, 2, 3, 4, 7, 8 |
| Replace "gaming" → "local" | Tasks 1, 2, 5, 7, 8 |
| Replace "proxmox" → "lxc-server" | Tasks 1, 2, 5, 7, 8 |
| Rename `.env.gaming` → `.env.local` | Task 1 |
| Rename `.env.proxmox` → `.env.lxc` | Task 1 |
| Remove Ryzen/hardware spec lines | Tasks 7, 8 |
| Remove OpenText/OTCS product references | Tasks 4, 8, 9 |
| Replace golden_dataset with generic examples | Task 6 |
| Add embedding model recommendation comment | Tasks 1, 2, 3 |
| Create `FEATURES.md` with 16 feature sections | Task 10 |
| Update `docs/INDEX.md` | Task 11 |
| Final verification scan | Task 11 |

**Placeholder scan:** No TBD, TODO, or vague instructions found.

**Type consistency:** No new code types introduced — pure text/JSON changes throughout.
