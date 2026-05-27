# Phase 13 Research: Docs Sync, README Languages

## Current State

### README.md (1,638 lines)
- Last meaningful update: Phase 4 (v1.0 era) — commit `d38eb41`
- **Missing features shipped since v1.0:**
  - SSE transport + starlette 1.0.0
  - Python 3.13 support (CI matrix: 3.11, 3.12, 3.13)
  - Health checks CLI (`kb-ingest check health`)
  - OTCS product auto-tagging (10 products)
  - Cross-encoder lazy loading (~10s faster startup)
  - Helm chart deployment
  - CI/CD pipeline (coverage gate, helm lint, logging audit, English audit)
  - English sweep (0 Portuguese)
  - Test count: 585 (not 491)
  - v1.3 milestone

### README.pt-BR.md (625 lines)
- Same age as README.md
- Follows different structure than English README (shorter, less detailed)
- Missing all v1.1/v1.2/v1.3 features

### README.es.md
- Does not exist yet

### docs/ (24 entries)
| Doc | Last Updated | Status |
|-----|-------------|--------|
| OPERATIONS.md | 2026-05-25 | ✅ Updated (Phase 9) |
| ARCHITECTURE.md | 2026-05-23 | ✅ Updated (Phase 8) |
| INDEX.md | 2026-05-23 | ✅ Updated (Phase 8) |
| REFERENCE.md | 2026-05-23 | ✅ Updated (Phase 8) |
| logging-audit.md | 2026-05-23 | ✅ Current |
| AUTO_INGESTION.md | 2026-05-16 | Stale (Phase 5 era) |
| TROUBLESHOOTING.md | 2026-05-16 | Stale |
| TESTING.md | 2026-05-15 | Stale |
| KUBERNETES.md | 2026-05-19 | Stale |
| MIGRATION.md | 2026-05-19 | Stale |
| SECURITY.md | 2026-05-19 | Stale |
| INSTRUCTIONS.md | 2026-05-19 | Stale |
| WEB_UI.md, QUERY_ANALYSIS.md, SEARCH_QUALITY.md, etc. | 2026-05-19 | Stale |

### Section Structure Comparison

**README.md sections:**
- Features, Quick Start (3 options), Production Deployment, Installation, Configuration, Usage (Ingest, Dir Structure, Auto-Ingestion, Version Filtering, Metadata Overrides), Health Checks, Service Management, Architecture, Monitoring, Operations, Development, Documentation, License

**README.pt-BR.md sections:**
- About, Quick Start (2 options), Installation, MCP Client Config, Basic Usage, MCP Tools, Architecture, Metrics & Monitoring

## Recommendations
1. README.md: Full refresh — update feature list, test counts, add v1.3 features, add English sweep badge
2. README.pt-BR.md: Sync structure with English README, translate new sections
3. README.es.md: Spanish translation following same structure
4. docs/: Fix stale docs (AUTO_INGESTION.md, TROUBLESHOOTING.md, TESTING.md, KUBERNETES.md) — minor updates only
