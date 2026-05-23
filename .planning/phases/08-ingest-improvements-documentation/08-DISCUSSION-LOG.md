# Phase 8: Ingest Improvements & Documentation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-23
**Phase:** 8-ingest-improvements-documentation
**Areas discussed:** OTCS Product Detection, Docstrings Pass Strategy, Documentation Content Plan

---

## OTCS Product Detection

| Option | Description | Selected |
|--------|-------------|----------|
| Just the 4 named | WebReports, xECM, Workflow, CSIDE only | |
| Expanded set | Include Content Server, Brava, OT2, Document Viewer, etc. | ✓ |
| Let me list them | User specifies OTCS product areas | |

**User's choice:** Expanded set
**Notes:** Researcher should enumerate the full OTCS product lineup and verify with the user during research.

| Option | Description | Selected |
|--------|-------------|----------|
| Directory-based only | Product from first path segment | |
| Filename-pattern only | Product from filename keywords | |
| Both, directory first | Directory takes priority, filename as fallback | ✓ |
| Both, with OTCS-specific config | Separate otcs_products.py file | |

**User's choice:** Both, directory first
**Notes:** Extends the existing `infer_product()` approach.

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in classifier.py | Unified PRODUCT_ALIASES / PRODUCT_FROM_NAME | ✓ |
| Separate otcs_products.py | Cleaner separation, new file | |

**User's choice:** Inline in classifier.py

---

## Docstrings Pass Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Translate all to English | Convert existing Portuguese docstrings | |
| Fill gaps only | Only add to undocumented, leave Portuguese | |
| Translate + fill gaps | Convert Portuguese AND fill missing | ✓ |

**User's choice:** Translate + fill gaps

| Option | Description | Selected |
|--------|-------------|----------|
| One-line minimum | Summary only, Args/Returns optional | |
| Full Google-style | Summary + Args + Returns + Raises | ✓ |

**User's choice:** Full Google-style

| Option | Description | Selected |
|--------|-------------|----------|
| Automated audit script | Script finds gaps, report for fixing | |
| Manual sweep | Read modules one by one | |
| Combined | Script identifies, fix in bulk | ✓ |

**User's choice:** Combined

---

## Documentation Content Plan

| Option | Description | Selected |
|--------|-------------|----------|
| Architecture + Ingest + Deploy | Focused update of key docs | |
| Plus QUICKSTART.md | Add quickstart guide | |
| Full docs refresh | Review all 22 docs for v1.1 accuracy | ✓ |

**User's choice:** Full docs refresh

| Option | Description | Selected |
|--------|-------------|----------|
| Mermaid | Text-based diagrams in markdown | ✓ |
| Excalidraw | Hand-drawn style | |
| Both | Mermaid for code, Excalidraw for overview | |

**User's choice:** Mermaid

---

## Agent's Discretion

- **CLI Status Command (INGEST-02)** — Not selected for discussion. Agent discretion for data sources (IngestRegistry SQLite ± Qdrant), output format (Rich table), and filtering options.

## Deferred Ideas

None — discussion stayed within phase scope.
