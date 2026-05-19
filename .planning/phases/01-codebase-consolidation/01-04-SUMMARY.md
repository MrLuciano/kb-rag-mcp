# CLEAN-04 / CLEAN-05 Summary

## What was done

1. **Moved `IngestRegistry` into `ingest/core/metadata.py`** — appended after `MetadataStore`. Added two new methods: `is_indexed()` and `mark_indexed()`.

2. **Deleted `ingest/registry.py`** — no longer exists.

3. **Fixed `batch_processor.py` SHA-256** — replaced `checksum="batch"` placeholder with real `IngestRegistry.sha256(file_path)` computation. Also fixed the registry loop to deduplicate per-file (avoiding multiple `mark_indexed` calls for the same file).

4. **Updated all callers** — `ingest/ingest.py` now imports from `ingest.core.metadata`.

5. **Added dedup tests** — `TestIngestRegistryDedup` in `tests/test_ingest_registry.py` with two passing tests.

## Test results

- Baseline: 42 failed, 288 passed
- After: 42 failed, 290 passed (+2 new passing tests, zero regressions)
