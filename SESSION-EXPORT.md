# KB-RAG-MCP Session Context Export
# Generated: 2026-05-28
# Purpose: Continue work on another machine

## Project: kb-rag-mcp
- Repo: https://github.com/MrLuciano/kb-rag-mcp.git
- Branch: master
- Latest commit: 9f0f55c (fix: add sys.path setup to audit_pdf_extractors)

## What was done this session

### 1. License formalization
- Created `LICENSE` file (MIT), updated `setup.py` with `license="MIT"` and classifier
- Commit: `b6cd79f`

### 2. PDF extraction audit script
- Created `scripts/audit_pdf_extractors.py` — measures docling success rate vs PyMuPDF fallback
- Now uses singleton `get_docling_converter()` from `ingest/docling_utils.py`
- Commit: `534b5c7`, updated in `9f0f55c`

### 3. Grafana dashboard provisioning fix
- Fixed `kb-rag.yaml` `path:` from provisioning config dir → dashboard JSON dir
- Narrowed docker-compose volume mount from `deployment/config/` to only `grafana-dashboard.json`
- Commit: `60e5d8a`

### 4. `data/` directory excluded from git
- Added to `.gitignore`, removed 168 tracked Qdrant binary files (~285 MB)
- Commit: `c621df7`

### 5. Docling dependency as optional extra
- `setup.py`: added `extras_require={"pdf": ["docling>=2.0.0"]}`
- `scripts/install-pdf-extras.sh` — Linux, GPU detection, CPU torch for AMD
- `scripts/install-pdf-extras.ps1` — Windows equivalent
- `scripts/remove-pdf-extras.sh` / `.ps1` — uninstall scripts with `--purge` flag
- Commit: `b7a270f` (install), `b4ec233` (uninstall)

### 6. Docling documentation
- Updated `docs/INSTRUCTIONS.md` and `docs/INSTRUCTIONS.pt-BR.md`:
  - "Instalação do docling" section with install/uninstall/GPU optimization
  - Extractors table footnote referencing docling section
  - `docs/REFERENCE.md` — PDF format table footnote
- Commit: `c63574f`, `b4ec233`

### 7. Docling performance optimization (CRITICAL)
- **Problem**: `DocumentConverter()` was created per PDF file → repeated HuggingFace model validation/download
- **Solution**: `ingest/docling_utils.py` — singleton `get_docling_converter()` with `@lru_cache`
  - Configures `AcceleratorOptions` via `PdfPipelineOptions`
  - Batch sizes: `ocr_batch_size=64`, `layout_batch_size=64` (defaults were 4)
  - `TableFormerMode.FAST` for faster table extraction
  - `RapidOcrOptions()` for CPU/ONNX OCR
  - Reads `DOCLING_DEVICE` and `DOCLING_NUM_THREADS` env vars
- `ingest/ingest.py`: `extract_pdf()` now uses singleton instead of `DocumentConverter()` per file
- `scripts/audit_pdf_extractors.py`: same pattern
- `scripts/download-docling-models.sh`: pre-downloads all models for offline use
- Commit: `5505521`

### 8. Benchmark results (5 PDFs, 53 pages total)

| Extractor     | Total    | ms/page | Chars    | vs baseline |
|---------------|----------|---------|----------|-------------|
| PyMuPDF       | 6.09s    | 115ms   | 69,815   | 1.0×        |
| PyMuPDF4LLM   | 21.26s   | 401ms   | 76,790   | 3.5×        |
| docling       | 156.37s  | 2,950ms | 128,051  | 25.7×       |

**Decision: PyMuPDF4LLM is NOT a compelling replacement for docling.**
- docling extracts 83% more text than PyMuPDF (tables, headings, structure)
- PyMuPDF4LLM only extracts 10% more text — GNN layout doesn't add much on our corpus
- Keep current docling→PyMuPDF fallback chain

### 9. Audit results with singleton converter

| PDF                                   | Size   | Time   | Notes               |
|---------------------------------------|--------|--------|---------------------|
| Release Notes (10 pg)                 | 0.3MB  | 35.79s | includes model init |
| KB0788610 (3 pg)                      | 0.3MB  | 4.79s  | steady-state        |
| KB0788722 (3 pg)                      | 0.3MB  | 4.68s  | steady-state        |
| Object Importer (36 pg)               | 0.4MB  | 107.6s | ~2.99s/page         |
| Certificate (1 pg)                    | 0.3MB  | 6.79s  |                     |

- First call: ~30s model load overhead (one-time)
- Steady-state avg: ~5.4s per small PDF
- **On GPU machine**: set `DOCLING_DEVICE=cuda`, expect 6-10× speedup

## Current state of key files

### ingest/docling_utils.py
Singleton DocumentConverter with GPU batch config. Key env vars:
- `DOCLING_ARTIFACTS_PATH` — persistent model cache directory
- `DOCLING_DEVICE` — auto/cpu/cuda/mps (default: auto)
- `DOCLING_NUM_THREADS` — CPU thread count (default: cpu_count)
- `HF_HUB_ENABLE_HF_TRANSFER=1` — faster HuggingFace downloads

### ingest/ingest.py:102-148
`extract_pdf()` — tries docling first via `get_docling_converter()`, falls back to PyMuPDF

### setup.py
`extras_require={"pdf": ["docling>=2.0.0"], "dev": [...]}`

### scripts/
- `install-pdf-extras.sh` / `.ps1` — GPU-aware install
- `remove-pdf-extras.sh` / `.ps1` — uninstall with `--purge`
- `download-docling-models.sh` — pre-download models for offline
- `audit_pdf_extractors.py` — benchmark script

## Important env vars for GPU machine

```bash
# .env additions for production GPU machine
DOCLING_ARTIFACTS_PATH=/path/to/models/docling
DOCLING_DEVICE=cuda
DOCLING_NUM_THREADS=8
HF_HUB_ENABLE_HF_TRANSFER=1
```

## Key technical details

- `DocumentConverter()` only accepts `allowed_formats` and `format_options` — NOT `accelerator_options`
- `AcceleratorOptions` must go inside `PdfPipelineOptions(accelerator_options=...)`
- Then `PdfFormatOption(pipeline_options=pdf_pipeline_options)` → `DocumentConverter(format_options={...})`
- Docling env vars: `DOCLING_` prefix, nested delimiter `_`, max split 1
- `docling` version 2.96.0 confirmed working
- typer pinned to `<0.22.0,>=0.12.5` (conflict with project's 0.25.x)

## Pre-existing test failures (NOT our changes)

- `tests/e2e/test_deployment_workflow.py`: expects `server/` dir (moved to `kb_server/`)
- `tests/e2e/test_deployment_workflow.py`: `EMBED_URL` missing from env template
- `tests/e2e/test_docker_compose.py`: prometheus scrape port 8000 vs 8080
- `tests/e2e/test_health_workflow.py`: `EmbeddingHealthCheck` import

## Next steps to continue on GPU machine

1. `git pull` on the other machine
2. `pip install -e ".[pdf]"` (or `./scripts/install-pdf-extras.sh`)
3. `./scripts/download-docling-models.sh` — pre-download models
4. Set env vars: `export DOCLING_DEVICE=cuda DOCLING_ARTIFACTS_PATH=models/docling`
5. Run audit: `python scripts/audit_pdf_extractors.py /path/to/corpus -r`
6. Compare GPU benchmark numbers vs CPU numbers from this session
7. Consider adjusting `ocr_batch_size` / `layout_batch_size` further based on GPU results