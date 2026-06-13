# Phase 29-04 SUMMARY: Git Connector

**Date:** 2026-06-10
**Type:** execute
**Status:** Complete

## Changes Made

### `ingest/connectors/git.py` — Git connector (new, ~330 lines)
- `GitConnector(ConnectorBase)` — clones/pulls git repos, extracts files
- **Auth:** HTTPS token (`x-access-token` embedded in URL) or SSH key (`GIT_SSH_COMMAND`)
- **Full sync:** `git clone` then `git ls-tree -r --name-only HEAD` for all files
- **Incremental sync:** `git pull --ff-only` + `git diff --name-only <since>..HEAD`
- **Content types:** .md/.rst → `text/markdown`; 30+ code/config extensions → `text/plain`; everything else skipped
- **File reading:** `git show <commit>:<path>` per file with HEAD commit SHA
- **Workspace management:** Auto-created temp dir cleaned up on `close()`
- **Factory registration:** Auto-registers as `"git"` on import

### `tests/test_git_connector.py` — 23 tests
- `_check_git_available` (available + not available)
- File discovery at HEAD and at specific commits (`git ls-tree`)
- `git diff` since commit (initial + second commit)
- File content reading at HEAD and earlier commits
- Document parsing for .md, .py, .yaml, unsupported exts
- `fetch_documents` (no checkpoint, with checkpoint, git unavailable, clone failure) — async
- `fetch_document` (found + not found) — async
- Content type detection for all supported extensions
- Checkpoint from HEAD SHA
- Factory registration verification

## Verification

| Suite | Result |
|---|---|
| `test_git_connector.py` | 23/23 passed |
| Full suite | 894 passed, 2 pre-existing failures |

## Registered Connectors

```bash
kb-rag connectors list
# → confluence, jira, git
```
