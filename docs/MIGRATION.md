# KB-RAG Migration Guide

Offline migration tools for moving KB state between environments or creating
point-in-time backups.

## What Gets Migrated

| Item | File in Package |
|---|---|
| Qdrant vector collection | `qdrant_snapshot.snapshot` |
| Job/metadata database | `kb_metadata.db` |
| File registry | `registry.db` (if present) |
| Config template | `env.template` |
| Integrity manifest | `manifest.json` (SHA256) |

## Prerequisites

- Source and target environments must have the same Qdrant version
- Qdrant must be running during export and import
- The `.venv` must be activated or `PYTHONPATH=.` set

## Export

```bash
./scripts/kb-migrate.sh export \
  --output /tmp/kb-backup-$(date +%Y%m%d).tar.gz \
  --qdrant-url http://localhost:6333 \
  --collection kb_docs
```

Or using Python directly:

```bash
PYTHONPATH=. python -m scripts.migrate.export \
  --output /tmp/kb-backup.tar.gz
```

## Validate

```bash
./scripts/kb-migrate.sh validate --package /tmp/kb-backup.tar.gz
```

Output on success: `[OK] Package valid. Files: manifest.json, qdrant_snapshot.snapshot, kb_metadata.db, env.template`

## Import

```bash
./scripts/kb-migrate.sh import \
  --package /tmp/kb-backup.tar.gz \
  --target-dir /opt/kb-rag/data \
  --qdrant-url http://target-host:6333 \
  --collection kb_docs
```

After import, review `env.template` and copy to `.env` with real values:

```bash
cp /opt/kb-rag/data/env.template /opt/kb-rag/.env
# Edit .env and replace <REPLACE_ME> values
```

## Skip Qdrant Restore (DB only)

```bash
./scripts/kb-migrate.sh import \
  --package /tmp/kb-backup.tar.gz \
  --target-dir /opt/kb-rag/data \
  --skip-qdrant
```

## Notes

- Export is offline-safe: Qdrant snapshot is atomic
- Import validates SHA256 checksums before restoring anything
- If import fails mid-way, target databases are not partially written (temp dir used)
- For large collections (>10 GB), ensure the target has enough disk space
- The Qdrant snapshot step is best-effort: if Qdrant is unavailable during export,
  the package is created without vector data (DBs only)
