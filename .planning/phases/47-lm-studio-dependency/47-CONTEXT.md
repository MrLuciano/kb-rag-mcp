# Phase 47: LM Studio Dependency Handling - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Add graceful fallback behavior when the embedding backend (LM Studio / Ollama / OpenAI-compat) is unreachable, plus a `kb-ingest check` CLI command to validate external dependencies at startup.

Requirements: T-02

</domain>

<decisions>
## Implementation Decisions

### Startup Health Check
- **D-01:** The existing `check_embedding_service()` in `kb_server/health.py` already pings the embedding backend. The server startup in `main()` should log a non-fatal warning when the backend is unreachable (already partially implemented in Phase 9 — verify current behavior).

### kb-ingest check CLI
- **D-02:** Extend the existing `kb-ingest check` command (already has `--health` and `--all` flags) to validate embedding backend connectivity before ingest operations.

### Graceful Degradation
- **D-03:** When embedding backend is unreachable:
  - Server starts successfully (no crash)
  - First query attempt returns clear error message: "Embedding backend unavailable — start LM Studio or check EMBED_BACKEND config"
  - Log a clear warning pointing to OPERATIONS.md for troubleshooting

### the agent's Discretion
- Whether the existing `check_embedding_service()` needs changes or just integration
- Error message wording for the user-facing fallback

</decisions>

<canonical_refs>
## Canonical References

- `kb_server/health.py` — Existing `check_embedding_service()` function
- `kb_server/server.py:1401-1409` — Existing pre-flight health check in main()
- `ingest/cli/check.py` — Existing `kb-ingest check` CLI command
- `kb_server/embed_client.py` — Embedding client

</canonical_refs>

---

*Phase: 47-lm-studio-dependency*
*Context gathered: 2026-06-15*
