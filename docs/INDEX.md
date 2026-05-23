# KB-RAG-MCP Documentation Index

**Complete documentation index for the KB-RAG-MCP project**

---

## Getting Started

- [README.md](../README.md) — Quick start, installation, usage
- [FEATURES.md](../FEATURES.md) — Complete feature reference — all 16 implemented features
- [REFERENCE.md](REFERENCE.md) — **Living reference: architecture, components, config, ops, QA results**
- [TESTING.md](TESTING.md) — Testing strategy and guidelines
- [CHANGELOG.md](CHANGELOG.md) — Release history and per-FASE change log
- [logging-audit.md](logging-audit.md) — Logging coverage report

## Technical Reference

- [INSTRUCTIONS.md](INSTRUCTIONS.md) — Complete technical instructions (EN)
- [INSTRUCTIONS.pt-BR.md](INSTRUCTIONS.pt-BR.md) — Instruções técnicas completas (PT-BR)
- [PLAN.md](PLAN.md) — Implementation roadmap (all 16 FASEs + QA pipeline)

## Topic Guides

- [SEARCH_QUALITY.md](SEARCH_QUALITY.md) — Hybrid search, reranking, evaluation methodology
- [AUTO_INGESTION.md](AUTO_INGESTION.md) — File watcher, version extractor, _meta.json overrides
- [VERSION_FILTERING.md](VERSION_FILTERING.md) — Version extraction and search filtering
- [METADATA_OVERRIDES.md](METADATA_OVERRIDES.md) — Per-directory metadata overrides
- [QUERY_ANALYSIS.md](QUERY_ANALYSIS.md) — Query telemetry and analysis
- [RAG_EVALUATION.md](RAG_EVALUATION.md) — RAGAS pipeline, golden dataset, metrics
- [WEB_UI.md](WEB_UI.md) — Web UI for document browsing and search testing
- [LEGACY_FORMATS.md](LEGACY_FORMATS.md) — Legacy Office (.doc/.xls/.ppt) and ZIP extraction rules
- [MIGRATION.md](MIGRATION.md) — Export, import, and validate knowledge base backups
- [OPERATIONS.md](OPERATIONS.md) — systemd services, backup, Prometheus, Grafana monitoring
- [KUBERNETES.md](KUBERNETES.md) — Kubernetes deployment guide (Helm chart, multi-collection)
- [SECURITY.md](SECURITY.md) — Threat model, hardening checklist, known limitations
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Common issues and fixes

## Historical Archive

FASE lifecycle docs (completion reports, per-FASE plans) are preserved in
[archive/](archive/) for historical reference.

---

## Roadmap Progress

| FASE | Title | Status |
|---|---|---|
| 1 | Foundation & Testing Infrastructure | ✅ Complete |
| 1.5 | Migration Tools | ✅ Complete |
| 2 | Job Management & Scheduler | ✅ Complete |
| 3 | Worker Pool & Rate Limiter | ✅ Complete |
| 4 | Progress & Observability | ✅ Complete |
| 5 | Cache System | ✅ Complete |
| 6 | CLI Refactor & Job Control | ✅ Complete |
| 7 | Document Validators & Quality | ✅ Complete |
| 8 | Connection Pooling & Batch Optimization | ✅ Complete |
| 9 | Production Hardening | ✅ Complete |
| 10 | Documentation & Final QA | ✅ Complete |
| 11 | Expanded Ingestion | ✅ Complete |
| 12 | Search Quality Enhancement | ✅ Complete |
| 13 | Ingestion Automation | ✅ Complete |
| 14 | Observability & Audit | ✅ Complete |
| 15 | Advanced Infrastructure | ✅ Complete |
| 16 | RAG Performance & Accuracy | ✅ Complete |
| QA | QA Evaluation Pipeline | ✅ Complete |
| v1.1-5 | CI Matrix & SSE Fixes | ✅ Complete |
| v1.1-6 | Test Isolation & Fixtures | ✅ Complete |
| v1.1-7 | Quality Gate & Logging Coverage | ✅ Complete |
| v1.1-8 | Ingest Improvements & Documentation | ✅ Wave 1 (OTCS tagging + Status CLI), Wave 2 (Docstrings + Docs refresh)

---

## Project Statistics

| Metric | Value |
|---|---|
| **Tests passing** | 585 |
| **Tests failing** | 0 |
| **Coverage target** | 90% branch (kb_server/ + ingest/) |
| **Phases completed** | 16 + QA pipeline |
| **QA Hit Rate** | 100% |
| **QA MRR** | 0.78 |

---

## How to Navigate

**New to the project?**
1. Read [REFERENCE.md](REFERENCE.md) — start here
2. Follow the Running the System section
3. Read [TESTING.md](TESTING.md) for test conventions

**Developer working on a feature?**
1. Check [REFERENCE.md](REFERENCE.md) for the component map and config
2. Read the relevant topic guide (e.g. SEARCH_QUALITY.md)
3. Run tests: `PYTHONPATH=. pytest`

**Understanding a past decision?**
1. Check [PLAN.md](PLAN.md) for the FASE spec
2. Check [archive/](archive/) for the completion report
3. Check [CHANGELOG.md](CHANGELOG.md) for the commit history
