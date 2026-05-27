# Milestone v1.2 — Project Summary

**Generated:** 2026-05-27
**Purpose:** Team onboarding and project review
**Status:** ✅ COMPLETE (2026-05-25)

---

## 1. Project Overview

### What This Is

kb-rag-mcp is a production-grade RAG (Retrieval-Augmented Generation) MCP server that connects AI assistants (Claude, Cursor, OpenCode, Copilot) to private, closed-source product documentation. Teams ingest their internal docs once and any AI tool with MCP support can query them with grounded, accurate answers. Built to be self-hosted by any team with any product documentation.

### Core Value

AI assistants stop hallucinating about closed-source products — every answer is grounded in the team's actual documentation.

### Milestone v1.2 Goal

Resolve accumulated technical debt from v1.0/v1.1 while adding automated document classification with Vendor/Product/Subsystem/Version extraction. This milestone focused on operational reliability (startup health checks, lazy loading, CI hardening) and intelligent document metadata extraction without LLM dependencies.

### Completion Status

**All 3 phases complete:**
- Phase 9: Startup Reliability (3/3 plans) — completed 2026-05-25
- Phase 10: CI & Test Infrastructure (3/3 plans) — completed 2026-05-25
- Phase 11: Auto-Classification (2/2 plans) — completed 2026-05-25

---

## 2. Architecture & Technical Decisions

### Key Technical Choices

- **Decision:** Cross-encoder lazy loading with regression tests
  - **Why:** Saves 500MB memory and ~10s startup latency; model loads only on first `predict()` call
  - **Phase:** 9 — Startup Reliability
  - **Pattern:** 4 regression tests verify `CrossEncoder` never constructed at import/init/empty-rerank

- **Decision:** Pre-flight health checks are non-fatal warnings
  - **Why:** Server starts even when Qdrant/LM Studio are down (useful for maintenance windows); operators get actionable warnings in logs
  - **Phase:** 9 — Startup Reliability
  - **Pattern:** Lazy import health functions inside `main()` to avoid circular imports

- **Decision:** Real qdrant_client model imports instead of MagicMock sys.modules stubs
  - **Why:** Eliminated 100+ lines of brittle test infrastructure; enum comparisons work correctly without `getattr(x, 'value', x)` workarounds
  - **Phase:** 10 — CI & Test Infrastructure
  - **Impact:** Zero test regressions (551 passed, 5 skipped)

- **Decision:** Helm chart validation in CI with `helm lint --strict`
  - **Why:** Catches structural errors before deployment; prevents manual-only chart review
  - **Phase:** 10 — CI & Test Infrastructure
  - **Pattern:** Separate `helm-lint` job with `azure/setup-helm@v4`

- **Decision:** Logging coverage CI gate at 40% threshold
  - **Why:** Below current 50.6% baseline (allows minor regression), above total collapse; prevents quality regression without blocking development
  - **Phase:** 10 — CI & Test Infrastructure
  - **Pattern:** `scripts/logging-audit.py --fail-under 40` on PR-to-master

- **Decision:** Heuristics-first classification (no LLM dependency)
  - **Why:** Fast, deterministic, zero API costs; LLM-assisted classification deferred to post-v1.2
  - **Phase:** 11 — Auto-Classification
  - **Pattern:** Filename → VENDOR_MAP → directory hierarchy → document metadata (lowest precedence)

- **Decision:** Vendor/Product/Subsystem/Version as distinct classification dimensions
  - **Why:** Enables fine-grained filtering in search queries; 15 products mapped to "OpenText" vendor via VENDOR_MAP
  - **Phase:** 11 — Auto-Classification
  - **Pattern:** `classify()` returns dict with vendor/product/subsystem/version/doc_type keys

- **Decision:** Document metadata gap-filling (PDF/DOCX title/author/subject/keywords)
  - **Why:** Enriches classification when filename is ambiguous; metadata has lowest precedence (never overrides explicit classification)
  - **Phase:** 11 — Auto-Classification
  - **Pattern:** `extract_document_metadata()` → `_build_metadata_text()` → `enrich_classification()`

### Tech Stack Evolution

**Added in v1.2:**
- `click.testing.CliRunner` — CLI command testing pattern
- `azure/setup-helm@v4` — CI Helm chart validation
- `argparse` — `--fail-under` flag in logging-audit.py

**Patterns Established:**
- Pre-flight health check: lazy import inside async function → call → log warning/info
- CLI command pattern: `click.group` → subcommand → Rich table/panel (check.py follows status.py)
- Lazy loading regression tests: mock `sys.modules` imports, assert `CrossEncoder` not called
- Source-level verification: grep/AST-based tests when integration is impractical

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 9 | Startup Reliability | ✅ Complete | Cross-encoder lazy loading hardened with regression tests, pre-flight health checks at server startup, kb-ingest check health CLI, and LM Studio embedding backend documentation |
| 10 | CI & Test Infrastructure | ✅ Complete | Helm chart validation in CI, MagicMock pollution fix for qdrant_client stubs, logging coverage CI enforcement with 40% threshold |
| 11 | Auto-Classification | ✅ Complete | Vendor/Product/Subsystem/Version auto-classification from filename patterns, directory hierarchy, and document metadata without LLM dependency |

---

## 4. Requirements Coverage

### All 9 v1.2 Requirements Met

**Startup Reliability (Phase 9):**
- ✅ **DEBT-01**: Cross-encoder lazy loading — server starts without loading model, first inference triggers load (~500MB saved, ~10s faster startup)
- ✅ **DEBT-04**: Pre-flight health checks — server logs warnings at startup if Qdrant or LM Studio unreachable
- ✅ **DEBT-06**: LM Studio embedding dependency documented in OPERATIONS.md with configuration, troubleshooting, and fallback options

**CI & Test Infrastructure (Phase 10):**
- ✅ **DEBT-02**: Helm chart validated with `helm lint --strict` in CI — catches structural errors before deployment
- ✅ **DEBT-03**: MagicMock pollution from qdrant_client stubs resolved — enum comparisons work without workarounds; 551 tests pass
- ✅ **DEBT-05**: Logging coverage enforced via CI gate with `--fail-under 40` threshold on PR-to-master

**Auto-Classification (Phase 11):**
- ✅ **CLASSIFY-01**: Documents auto-classified with Vendor, Product, Subsystem, and Version attributes from filename patterns and directory hierarchy
- ✅ **CLASSIFY-02**: Classification gaps filled by extracting metadata (title, subject, author, keywords) from PDF/DOCX files
- ✅ **CLASSIFY-03**: Backward-compatible with existing OTCS auto-tagging — `infer_product()`, `infer_doc_type()`, `classify()` signatures unchanged

### Success Criteria Verification

**Phase 9:**
- ✅ Server starts without loading cross-encoder model — verified via startup logs + 4 regression tests
- ✅ Pre-flight health checks log warnings for unreachable services (non-fatal)
- ✅ `kb-ingest check health` CLI validates all external dependencies
- ✅ LM Studio embedding backend documented with 4 backend options, configuration, troubleshooting

**Phase 10:**
- ✅ `helm lint deployment/helm/kb-rag-mcp/ --strict` exits 0 in CI
- ✅ All qdrant_client enum comparisons work correctly — zero `getattr(x, 'value', x)` workarounds needed
- ✅ Logging audit script has `--fail-under` flag; CI enforces 40% threshold
- ✅ Full test suite passes: 551 passed, 5 skipped, 0 failed

**Phase 11:**
- ✅ SC1: `"OpenText WebReport Administrator Guide 23.4.pdf"` → vendor=OpenText, product=WebReports, version=23.4, doc_type=admin_guide
- ✅ SC2: Ambiguous filename with rich PDF metadata → all gaps filled from title/author/subject
- ✅ SC3: `infer_product()`, `infer_doc_type()` signatures unchanged — 585 tests pass with zero regressions
- ✅ Bug fix: `DOC_TYPE_RULES` standard patterns use word boundaries — no more "nist" false positive in "Administrator"

---

## 5. Key Decisions Log

| ID | Decision | Rationale | Phase | Outcome |
|----|----------|-----------|-------|---------|
| D-09-01 | Pre-flight health checks are non-fatal warnings | Server starts even when dependencies are down (useful for maintenance) | 9 | ✅ Operators get actionable warnings without service interruption |
| D-09-02 | Health functions imported lazily inside main() | Avoids circular imports at module level | 9 | ✅ No import cycle issues; clean module structure |
| D-09-03 | CLI check command patterns after status.py | Consistency across CLI subcommands | 9 | ✅ Uniform UX; Rich table/panel pattern reused |
| D-09-04 | Unit tests validate health check logic, not main() | main() starts a server; testing logic pattern instead | 9 | ✅ Fast, isolated tests; source-level verification for integration |
| D-10-01 | Real qdrant_client imports instead of MagicMock stubs | Eliminates 100+ lines of brittle test infrastructure | 10 | ✅ Zero regressions; enum comparisons work correctly |
| D-10-02 | Helm lint in CI with azure/setup-helm@v4 | Catches chart errors before deployment | 10 | ✅ Chart validation on every push/PR |
| D-10-03 | Logging audit threshold at 40% | Below current 50.6%, above total regression | 10 | ✅ Quality gate without blocking development |
| D-11-01 | Heuristics-first classification (no LLM) | Fast, deterministic, zero API costs | 11 | ✅ LLM-assisted classification deferred to future milestone |
| D-11-02 | Vendor/Product/Subsystem/Version as distinct dimensions | Enables fine-grained search filtering | 11 | ✅ 15 products mapped to "OpenText" vendor via VENDOR_MAP |
| D-11-03 | Document metadata enrichment at lowest precedence | Never overrides explicit classification | 11 | ✅ Gap-filling without false positives |
| D-11-04 | Word boundaries in DOC_TYPE_RULES | Prevents "nist" substring match in "Administrator" | 11 | ✅ Zero false positives on standard doc types |

---

## 6. Tech Debt & Deferred Items

### Tech Debt Resolved in v1.2

- ✅ **DEBT-01**: Cross-encoder lazy loading — hardened with 4 regression tests
- ✅ **DEBT-02**: Helm chart validation — automated in CI
- ✅ **DEBT-03**: MagicMock pollution — replaced with real imports
- ✅ **DEBT-04**: Pre-flight health checks — implemented with non-fatal warnings
- ✅ **DEBT-05**: Logging coverage CI gate — 40% threshold enforced
- ✅ **DEBT-06**: LM Studio embedding docs — comprehensive OPERATIONS.md section

### Deferred to Future Milestones

- **LLM-assisted classification** — heuristics-first approach works well; LLM enhancement for ambiguous documents deferred to post-v1.2
- **Higher logging coverage threshold** — 40% baseline is conservative; aspirational target (70%+) deferred to avoid blocking development
- **Integration tests for main()** — source-level verification chosen instead; full integration tests for server startup deferred

### Lessons Learned (from RETROSPECTIVE.md context)

- **Pre-flight checks should be non-fatal** — maintenance windows and partial outages shouldn't block server startup
- **Real imports > sys.modules mocks** — eliminating MagicMock stubs improved test clarity and eliminated workarounds
- **Threshold-based quality gates need breathing room** — 40% logging coverage allows minor regression without blocking PRs
- **Heuristics beat LLMs for structured data** — filename/directory patterns + metadata extraction solved 95% of classification needs without API costs

---

## 7. Getting Started

### Run the Project

**Prerequisites:**
- Python 3.11+
- Qdrant (Docker via `docker-compose.yml` or embedded mode)
- LM Studio or Ollama (embedding backend)

**Quick Start:**
```bash
# Clone and setup
git clone https://github.com/MrLuciano/kb-rag-mcp.git
cd kb-rag-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start Qdrant
docker-compose up -d

# Configure environment
cp config/.env.template .env
# Edit .env: set QDRANT_URL, EMBED_BACKEND, MODEL_NAME

# Health check
kb-ingest check health

# Ingest documents
kb-ingest ingest --docs /path/to/docs --product MyProduct

# Start MCP server
python -m kb_server.server
```

### Key Directories

- **`kb_server/`** — MCP server, retrieval pipeline, vector store abstraction
  - `server.py` — MCP tool handlers (search_kb, list_documents, get_chunk, kb_stats)
  - `retrieval/` — Hybrid search (BM25+dense), reranking, query analysis
  - `vector_store.py` — Qdrant abstraction layer
  - `embed_client.py` — Multi-backend embedding (LM Studio, Ollama, OpenAI-compat)
  - `collections/` — Collection routing and lifecycle management

- **`ingest/`** — Document ingestion pipeline
  - `ingest.py` — Main ingestion orchestrator
  - `classifier.py` — Document classification (vendor/product/subsystem/doc_type/version)
  - `parsers/` — File extractors (PDF, DOCX, XLSX, PPTX, ODT, markdown, text)
  - `core/metadata.py` — IngestRegistry (SQLite dedup, status tracking)
  - `cli/` — CLI commands (ingest, status, check health, reclassify)
  - `worker/` — Async batch processing
  - `validation/` — Ingestion validation pipeline

- **`tests/`** — 585 passing tests (518 unit, 67 integration/E2E)
  - `conftest.py` — Mock fixtures (Qdrant, embed client, Redis)
  - `test_*.py` — Unit tests for all modules
  - `e2e/` — End-to-end integration tests

- **`docs/`** — Operational documentation
  - `ARCHITECTURE.md` — System architecture with Mermaid diagrams
  - `OPERATIONS.md` — Deployment, configuration, health checks, troubleshooting
  - `REFERENCE.md` — API reference for MCP tools
  - `KUBERNETES.md` — Helm chart deployment guide

### Tests

```bash
# Run all unit tests (no external services required)
pytest -m "not integration"

# Run full suite (requires Qdrant + LM Studio running)
pytest tests/ --ignore=tests/e2e --ignore=tests/test_sse_handler.py

# Run SSE tests (separate process due to stub conflicts)
pytest tests/test_sse_handler.py

# Run E2E tests (requires full stack)
pytest tests/e2e/

# Coverage report
pytest --cov=kb_server --cov=ingest --cov-report=html
```

### Where to Look First

**New contributors should start here:**

1. **Entry point:** `kb_server/server.py` — MCP tool registration and dispatch
2. **Search flow:** `kb_server/retrieval/hybrid_search.py` — Dense + BM25 RRF fusion
3. **Ingestion flow:** `ingest/ingest.py` → `ingest/classifier.py` → `kb_server/vector_store.py`
4. **Classification logic:** `ingest/classifier.py` — Vendor/product/subsystem/doc_type/version inference
5. **Health checks:** `kb_server/server.py::main()` + `ingest/cli/check.py`

**Key interfaces:**
- `VectorStore` — Single abstraction for Qdrant operations (search, upsert, list, stats)
- `classify()` — Main classification entry point (filename + metadata → structured dict)
- `get_embedding()` / `get_embeddings_batch()` — Backend-agnostic embedding generation
- `IngestRegistry` — SQLite-backed dedup and status tracking

---

## Stats

- **Timeline:** 2026-05-14 → 2026-05-25 (11 days)
- **Phases:** 3/3 complete (9-11)
- **Plans:** 8/8 complete (3+3+2)
- **Commits:** 17 feature commits
- **Files changed:** 28 files (+3,409 insertions / -171 deletions)
- **Tests:** 585 passing, 5 skipped, 0 failures (zero regressions from v1.1)
- **Coverage:** 90% branch on kb_server/ + ingest/ (maintained from v1.1)
- **Contributors:** 1 (Luciano Marinho)

### Phase Breakdown

| Phase | Plans | Tasks | Duration | Files Modified | Key Deliverable |
|-------|-------|-------|----------|----------------|-----------------|
| 9 | 3 | 6 | 18 min | 8 (4 created, 4 modified) | Pre-flight health checks + CLI health command |
| 10 | 3 | 6 | ~45 min | 7 (0 created, 7 modified) | Helm lint CI + MagicMock cleanup + logging gate |
| 11 | 2 | 8 | ~90 min | 13 (0 created, 13 modified) | Auto-classification with vendor/product/subsystem/version |

### Requirements Traceability

- **DEBT-01 through DEBT-06:** 6/6 resolved
- **CLASSIFY-01 through CLASSIFY-03:** 3/3 complete
- **Total:** 9/9 v1.2 requirements satisfied

---

## What's Next

**Milestone v1.3** (already shipped 2026-05-26):
- English-only codebase enforcement
- Multilingual README (Spanish)
- Health dashboard UI
- PowerShell Windows LAN access script
- Document reclassification capability

**Getting Involved:**
- Review `.planning/ROADMAP.md` for current milestone status
- Check `.planning/REQUIREMENTS.md` for active requirements
- Read `.planning/RETROSPECTIVE.md` for lessons learned
- Join development: see `CONTRIBUTING.md` for workflow and conventions

---

_Generated from completed milestone artifacts for team onboarding._
_All technical decisions and architecture choices are grounded in actual implementation from phase SUMMARY, CONTEXT, and VERIFICATION files._
