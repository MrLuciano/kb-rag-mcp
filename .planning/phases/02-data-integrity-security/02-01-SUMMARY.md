# 02-01: File-deletion vector cleanup in file watcher (DATA-01)

## Status: DONE

## Changes

### `ingest/watcher/file_watcher.py`
- Added `Optional` to typing imports
- Added `delete_handler: Optional[Callable[[str], None]] = None` parameter to `DocWatcher.__init__`
- Stored as `self.delete_handler`
- Replaced `on_deleted` stub with full implementation: calls handler when set, catches and logs exceptions
- `main()` now wires `VectorStore`, `IngestRegistry`, and `_delete_handler` closure, passes it to `DocWatcher`

### `tests/test_file_watcher.py`
- Replaced `test_on_deleted_logs_only` with four new tests:
  - `test_on_deleted_no_handler` — no handler is a no-op
  - `test_on_deleted_with_handler_calls_callback` — handler called with file path
  - `test_on_deleted_ignored_file_skips_handler` — ignored files skip handler
  - `test_on_deleted_handler_exception_does_not_propagate` — exceptions caught

## Test Results

18/18 tests pass in `tests/test_file_watcher.py`, no regressions.

## Commit

`3a056ee feat: file watcher on_deleted cleans up Qdrant vectors (DATA-01)`
