---
phase: 11
name: Auto-Classification
milestone: v1.2
status: completed
plans: 2
requirements: [CLASSIFY-01, CLASSIFY-02, CLASSIFY-03]
---

# Phase 11 Summary: Auto-Classification

## Execution
- **Waves:** 2 (Wave 1: 11-01 vendor/subsystem; Wave 2: 11-02 metadata + ingest)
- **Commits: 4**
  - `2d3ed8f` — feat(11-auto-classification): add vendor and subsystem inference to classifier
  - `43eeaa8` — feat(11-auto-classification): add document metadata extraction for PDF and DOCX
  - `1497002` — feat(11-auto-classification): add enrich_classification() for gap-filling from document metadata
  - `7392243` — feat(11-auto-classification): integrate vendor and subsystem into ingest pipeline

## Plans Delivered

### 11-01: Vendor and subsystem inference
- `VENDOR_MAP`: 15 products mapped (14 OTCS → "OpenText", ISO → "ISO")
- `FILENAME_VENDOR_PATTERNS`: Detects "OpenText" and "OT-" / "OT_" prefixes
- `SUBSYSTEM_PATTERNS`: 8 categories (API, Security, Admin, Integration, Migration, Install, Reporting, Performance)
- `infer_vendor()`: Filename → VENDOR_MAP → parent directory → ""
- `infer_subsystem()`: Subdirectory → filename patterns → ""
- `classify()` now returns vendor and subsystem keys
- Bug fix: `DOC_TYPE_RULES` standard patterns got word boundaries — no more "nist" false positive in "Administrator"
- 135 new lines of tests; SC1 passes end-to-end

### 11-02: Metadata extraction, enrichment, ingest integration
- `extract_document_metadata()`: title/author/subject/keywords from PDF (PyMuPDF) and DOCX (python-docx)
- `_build_metadata_text()` helper for gap-filling
- `enrich_classification()`: Gap-fills vendor/product/doc_type from document metadata (lowest precedence)
- Integrated into `classify()` — enrichment runs after _meta.json and auto-classification
- Ingest pipeline stores vendor/subsystem in Qdrant chunk payload (`ingest/ingest.py`, `ingest/worker/batch_processor.py`)
- Bug fix: `_classify_from_metadata_text` was passing "geral" as product_override — now only passes non-default values
- 7 metadata tests + 7 enrichment tests

## Requirements Coverage

| REQ-ID | Description | Status |
|--------|-------------|--------|
| CLASSIFY-01 | Auto-classify Vendor/Product/Subsystem/Version | ✅ |
| CLASSIFY-02 | Gap-fill from PDF/DOCX metadata | ✅ |
| CLASSIFY-03 | Backward-compatible signatures | ✅ |

## Verifications
- SC1: `"OpenText WebReport Administrator Guide 23.4.pdf"` → vendor=OpenText, product=WebReports, version=23.4, doc_type=admin_guide ✅
- SC2: Ambiguous filename with rich PDF metadata → all gaps filled ✅
- SC3: `infer_product()`, `infer_doc_type()` signatures unchanged ✅
- **585 passed, 5 skipped** — zero regressions across all test files

## State
- STATE.md: Phase 11 → COMPLETE (2/2 plans)
- ROADMAP.md: 11-01 ✅, 11-02 ✅, v1.2 milestone shipped
- REQUIREMENTS.md: CLASSIFY-01/02/03 ✅
- Progress: 33% (4/12 phases, 15/16 plans)
- Milestone v1.2: **COMPLETE** — all 9 requirements (DEBT-01 through CLASSIFY-03) satisfied
