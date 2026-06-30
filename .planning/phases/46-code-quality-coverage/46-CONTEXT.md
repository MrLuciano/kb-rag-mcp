# Phase 46: Code Quality & Coverage - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix code quality baseline: migrate datetime.utcnow() to timezone-aware API, tag pre-existing test failures as integration tests, and remove unused imports.

Requirements: Q-01, Q-04, Q-05

</domain>

<decisions>
## Implementation Decisions

### Q-01: datetime.utcnow() deprecation
- **D-01:** Replace all 23 `datetime.utcnow()` calls across `kb_server/`, `ingest/`, and `tests/` with `datetime.now(timezone.utc).replace(tzinfo=None)` — produces timezone-naive UTC datetimes compatible with SQLite/SQLAlchemy while using the non-deprecated API.

### Q-04: Integration test tagging
- **D-02:** Add `pytest.mark.integration` decorator to the 5 failing tests in `tests/test_smoke.py` and `tests/test_server_terms.py` that require Qdrant. Configure pytest to skip integration-tagged tests by default in `pyproject.toml`.

### Q-05: Unused imports
- **D-03:** Remove unused imports identified by flake8 F401 across `kb_server/` and `ingest/`.

### the agent's Discretion
- Whether to fix flake8 W293 (blank line whitespace) and E501 (line length) violations discovered during the unused import cleanup.
</decisions>

<canonical_refs>
## Canonical References

- `REVIEW.md` §Quality — Full audit findings
- `pyproject.toml` — pytest markers configuration
</canonical_refs>

---

*Phase: 46-code-quality-coverage*
*Context gathered: 2026-06-15*
