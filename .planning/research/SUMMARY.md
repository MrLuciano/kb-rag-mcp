# Research Summary: Auto-Classification for Document Ingestion

**Milestone:** v1.2 Tech Debt & Classification
**Feature:** B-05 — Vendor/Product/Subsystem/Version auto-classification
**Date:** 2026-05-25

## Key Findings

### 1. Heuristics-First Priority Chain (Industry Standard)
Multiple projects (docflow, alchemia-ingestvm, distillcore) use a priority-chain approach:
1. **Directory name** → highest confidence (1.0)
2. **Filename pattern** → high confidence with regex anchoring
3. **First-page content** → medium confidence (heuristic keyword scan)
4. **LLM enrichment** → optional, never overrides heuristics

**Our existing code already implements steps 1-2** in `ingest/classifier.py` (`infer_product()` with directory-first, filename-fallback). The extension adds Vendor, Subsystem, Version dimensions.

### 2. Extracting Version from Filenames
Structured naming patterns like `OpenText Documentum Webtop Administrator Guide 23.4.pdf` are common. Version extraction should:
- Match `\d+\.\d+(\.\d+)?` patterns at filename end
- Match `v\d+` or `ver\d+` prefixes
- Use known version keywords: "Version", "v.", "Release", "R"

### 3. First-Page Content Scanning
PDF/DOCX metadata and first-page content (title, headers, footers, subject) can provide:
- Vendor name (e.g., "OpenText")
- Product name (e.g., "Documentum Webtop")
- Document type (e.g., "Administrator Guide")
- Version (e.g., "23.4")

Already available extractors: PyMuPDF (PDF metadata), python-docx (DOCX metadata).

### 4. LLM as Optional Enrichment
docflow's approach: "LLM suggestions are optional enrichment and never override deterministic decisions." For our use case, LLM could suggest classifications for ambiguous files, but heuristics handle the common path.

### 5. Existing Foundation
- `ingest/classifier.py` has `infer_product()`, `infer_doc_type()`, `classify()` — extends naturally
- `ingest/core/metadata.py`'s `IngestRegistry` stores metadata — version field already exists as `version_id`
- PDF metadata extraction via PyMuPDF already available
- First-page text extraction via existing parsers

## Architecture Recommendation

```
Extension to ingest/classifier.py:

classify_extended(filepath) → {
  vendor: str | None,       # "OpenText"
  product: str | None,      # "WebReports"
  subsystem: str | None,    # "Server"
  doc_type: str,            # "admin_guide"
  version: str | None       # "23.4"
}

Priority chain:
1. Directory path → Vendor + Product (existing, extends OTCS)
2. Filename pattern → Product + Version + DocType (existing, extends PRODUCT_FROM_NAME)
3. PDF/DOCX metadata → Vendor + Product + Version (new, extract from subject/author/title)
4. First-page text scan → Vendor + Product + Version (new, keyword matching)
```

## What NOT to Do
- No new dependencies — use existing PyMuPDF/python-docx for metadata
- No LLM integration in v1.2 — defer to future milestone if needed
- No changes to existing `infer_product()`/`infer_doc_type()` signatures — add new functions
