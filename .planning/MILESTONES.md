# Milestones

## v1.0 — Release-Readiness

**Shipped:** 2026-05-19
**Phases:** 4 | **Plans:** 13 | **Tests:** 491 passing

### Delivered

Made kb-rag-mcp safe to release publicly: deleted legacy `server/` module, fixed real BM25 hybrid search, unified env loading, hardened data integrity (file-watcher deletion, secrets), raised test coverage to 88% branch with full CI, and shipped Dockerfile + quickstart.sh + new README getting-started guide.

### Key Accomplishments

1. `kb_server/` is now the single canonical module — `server/` and `ingest/registry.py` deleted
2. Real BM25+dense RRF hybrid search — sparse path was dead code before this milestone
3. 491 tests passing, 88% branch coverage on `kb_server/` (up from ~50% pre-milestone)
4. GitHub Actions CI on every push/PR; integration tests cover ingest→search and multi-collection routing
5. Multi-stage Dockerfile + `scripts/quickstart.sh` — zero-to-running setup in one command
6. Secrets fully removed from git tracking; `CONTRIBUTING.md` documents remediation for teams

### Stats

- Timeline: 2026-05-14 → 2026-05-19 (5 days)
- Files changed: 308 | Python LOC: ~251k | Commits: 103
- Requirements: 15/15 v1 requirements met

### Git Tag

`v1.0`
