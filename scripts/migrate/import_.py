"""
Import KB-RAG state from a .tar.gz migration package.

What gets restored:
- Qdrant collection snapshot (via Qdrant REST API upload)
- kb_metadata.db → target_dir/kb_metadata.db
- registry.db → target_dir/registry.db (if present)
- env.template → target_dir/env.template (for manual review)

Usage:
    python -m scripts.migrate.import_ --package /tmp/kb-backup.tar.gz \\
        --target-dir /opt/kb-rag/data
"""
import argparse
import os
import shutil
import tarfile
import tempfile
from pathlib import Path

from scripts.migrate.validate import validate_package


def restore_qdrant_snapshot(qdrant_url: str, collection: str, snapshot_path: Path) -> None:
    """Upload and restore a Qdrant snapshot to the target collection."""
    import httpx

    with open(snapshot_path, "rb") as f:
        resp = httpx.post(
            f"{qdrant_url}/collections/{collection}/snapshots/upload",
            files={"snapshot": (snapshot_path.name, f, "application/octet-stream")},
            timeout=300,
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"Qdrant snapshot restore failed: {resp.status_code} {resp.text}")
    print(f"[import] Qdrant snapshot restored to collection '{collection}'")


def import_kb(
    package: Path,
    target_dir: Path,
    qdrant_url: str = "http://localhost:6333",
    collection: str = "kb_docs",
    skip_qdrant: bool = False,
) -> None:
    """
    Restore KB state from a .tar.gz migration package.

    Args:
        package: Source .tar.gz package path
        target_dir: Directory to restore databases into
        qdrant_url: Qdrant base URL
        collection: Target collection name
        skip_qdrant: If True, skip Qdrant snapshot restore (DBs only)

    Raises:
        ValueError: If package fails validation
    """
    package = Path(package)
    target_dir = Path(target_dir)

    # Validate first — raises ValueError if invalid
    result = validate_package(package)
    if not result["valid"]:
        raise ValueError(f"Package is invalid: {result['errors']}")

    target_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(package, "r:gz") as tar:
            safe_members = [
                m for m in tar.getmembers()
                if not os.path.isabs(m.name) and ".." not in m.name
            ]
            tar.extractall(tmp_path, members=safe_members)

        # Restore DBs
        for db_name in ["kb_metadata.db", "registry.db"]:
            src = tmp_path / db_name
            if src.exists():
                dest = target_dir / db_name
                shutil.copy2(src, dest)
                print(f"[import] Restored {db_name} → {dest}")

        # Copy env template for review
        env_tmpl = tmp_path / "env.template"
        if env_tmpl.exists():
            shutil.copy2(env_tmpl, target_dir / "env.template")
            print(f"[import] env.template copied to {target_dir}/env.template — review and rename to .env")

        # Restore Qdrant snapshot
        if not skip_qdrant:
            snap = tmp_path / "qdrant_snapshot.snapshot"
            if snap.exists():
                restore_qdrant_snapshot(qdrant_url, collection, snap)
            else:
                print("[import] WARNING: No Qdrant snapshot found in package")

    print(f"[import] Import complete. Data restored to {target_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import KB-RAG state from .tar.gz")
    parser.add_argument("--package", required=True, help="Source .tar.gz package")
    parser.add_argument("--target-dir", required=True, help="Directory to restore databases into")
    parser.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", "http://localhost:6333"))
    parser.add_argument("--collection", default=os.getenv("QDRANT_COLLECTION", "kb_docs"))
    parser.add_argument("--skip-qdrant", action="store_true", help="Skip Qdrant snapshot restore")
    args = parser.parse_args()

    import_kb(
        package=Path(args.package),
        target_dir=Path(args.target_dir),
        qdrant_url=args.qdrant_url,
        collection=args.collection,
        skip_qdrant=args.skip_qdrant,
    )
