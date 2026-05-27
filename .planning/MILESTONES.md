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

---

## v1.1 — Quality & Operational Excellence

**Shipped:** 2026-05-23
**Phases:** 4 (5-8) | **Plans:** 10 | **Tests:** 576 passing

### Delivered

Established operational maturity and code quality foundations: SSE stability with Python 3.13 support, full test isolation from external services, 90% branch coverage enforcement on PR-to-master, OTCS product auto-tagging for 10 OpenText products, and English-only codebase with comprehensive Google-style docstrings.

### Key Accomplishments

1. **SSE stability & Python 3.13 support** — Fixed NoneType crash in SSE handler, pinned Starlette ≥1.0.0, added CI matrix testing across Python 3.11/3.12/3.13
2. **Full test isolation** — Added 3 session-scoped mock fixtures (Qdrant, embed client, Redis) enabling `pytest -m "not integration"` to run without external services; 518 unit tests pass without infrastructure
3. **90% coverage enforcement** — Set `fail_under = 90` in pyproject.toml and CI, enforcing branch coverage on PR-to-master for both kb_server/ and ingest/
4. **OTCS product auto-tagging** — Added 18 directory aliases and 10 filename patterns enabling auto-detection of 10 OpenText product areas (ContentServer, WebReports, xECM, Workflow, CSIDE, Brava, OT2, DocumentViewer, APIGateway, ArchiveCenter)
5. **CLI status command** — Added `kb-ingest status` with Rich table output showing per-source file/chunk/error counts, with optional `--source` filtering
6. **English-only codebase** — Fixed 105 docstring gaps (32 missing + 73 Portuguese → English), verified with AST-based audit script; all public methods now have Google-style docstrings

### Stats

- Timeline: 2026-05-14 → 2026-05-23 (8 days)
- Files changed: 75 | +4,980 insertions, -3,106 deletions | Python LOC: 13,457
- Requirements: 15/15 v1.1 requirements met
- Commits: 16 feature commits

### Git Tag

`v1.1`
