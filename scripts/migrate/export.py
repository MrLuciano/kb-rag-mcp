"""
Export KB-RAG state to a portable .tar.gz migration package.

What gets exported:
- Qdrant collection snapshot (.snapshot file)
- kb_metadata.db (job system, metadata schema)
- registry.db (file registry, if present)
- env.template (sanitized copy of .env without secrets)
- manifest.json (SHA256 checksums of all files)

Usage:
    python -m scripts.migrate.export --output /tmp/kb-backup.tar.gz
    python -m scripts.migrate.export --output /tmp/kb-backup.tar.gz \\
        --qdrant-url http://localhost:6333 --collection kb_docs
"""
import argparse
import hashlib
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path


def _take_qdrant_snapshot(qdrant_url: str, collection: str, out_dir: str) -> Path:
    """Take a Qdrant collection snapshot and download it to out_dir."""
    from qdrant_client import QdrantClient

    client = QdrantClient(url=qdrant_url)
    snapshot_info = client.create_snapshot(collection_name=collection)
    snapshot_name = snapshot_info.name

    # Download snapshot via HTTP
    import httpx
    resp = httpx.get(
        f"{qdrant_url}/collections/{collection}/snapshots/{snapshot_name}",
        timeout=300,
    )
    resp.raise_for_status()
    out_path = Path(out_dir) / f"{collection}_{snapshot_name}"
    out_path.write_bytes(resp.content)
    return out_path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sanitize_env(env_path: Path) -> str:
    """Return sanitized .env content with secret values redacted."""
    SECRET_KEYS = {"LMS_BASE_URL", "REDIS_URL", "REDIS_PASSWORD"}
    lines = []
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            lines.append(line)
            continue
        if "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in SECRET_KEYS:
                lines.append(f"{key}=<REPLACE_ME>")
                continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def export_kb(
    output: Path,
    metadata_db: Path | None = None,
    registry_db: Path | None = None,
    qdrant_url: str = "http://localhost:6333",
    collection: str = "kb_docs",
    env_file: Path | None = None,
) -> None:
    """
    Export KB state to output .tar.gz package.

    Args:
        output: Destination .tar.gz path
        metadata_db: Path to kb_metadata.db (auto-detected if None)
        registry_db: Path to registry.db (optional, skipped if not found)
        qdrant_url: Qdrant base URL
        collection: Collection name to snapshot
        env_file: .env path (auto-detected if None)
    """
    output = Path(output)
    project_root = Path(__file__).parent.parent.parent

    if metadata_db is None:
        metadata_db = project_root / "kb_metadata.db"
    if env_file is None:
        env_file = project_root / ".env"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifest: dict[str, str] = {}

        # 1. Qdrant snapshot
        print(f"[export] Taking Qdrant snapshot for collection '{collection}'...")
        try:
            snap_path = _take_qdrant_snapshot(qdrant_url, collection, tmp)
            dest = tmp_path / "qdrant_snapshot.snapshot"
            shutil.copy2(snap_path, dest)
            manifest["qdrant_snapshot.snapshot"] = _sha256(dest)
            print(f"[export] Snapshot: {dest.stat().st_size / 1024 / 1024:.1f} MB")
        except Exception as e:
            print(f"[export] WARNING: Qdrant snapshot failed: {e}")

        # 2. Metadata DB
        if Path(metadata_db).exists():
            dest = tmp_path / "kb_metadata.db"
            shutil.copy2(metadata_db, dest)
            manifest["kb_metadata.db"] = _sha256(dest)
            print(f"[export] Metadata DB: {dest.stat().st_size / 1024:.0f} KB")

        # 3. Registry DB (optional)
        if registry_db and Path(registry_db).exists():
            dest = tmp_path / "registry.db"
            shutil.copy2(registry_db, dest)
            manifest["registry.db"] = _sha256(dest)

        # 4. Env template (sanitized)
        if env_file and Path(env_file).exists():
            content = _sanitize_env(Path(env_file))
            dest = tmp_path / "env.template"
            dest.write_text(content)
            manifest["env.template"] = _sha256(dest)

        # 5. Write manifest (does NOT include itself)
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        # 6. Bundle into .tar.gz
        output.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(output, "w:gz") as tar:
            for f in tmp_path.iterdir():
                tar.add(f, arcname=f.name)

    print(f"[export] Package written: {output} ({output.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export KB-RAG state to .tar.gz")
    parser.add_argument("--output", required=True, help="Output .tar.gz path")
    parser.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", "http://localhost:6333"))
    parser.add_argument("--collection", default=os.getenv("QDRANT_COLLECTION", "kb_docs"))
    parser.add_argument("--metadata-db", default=None)
    parser.add_argument("--registry-db", default=None)
    args = parser.parse_args()

    export_kb(
        output=Path(args.output),
        metadata_db=Path(args.metadata_db) if args.metadata_db else None,
        registry_db=Path(args.registry_db) if args.registry_db else None,
        qdrant_url=args.qdrant_url,
        collection=args.collection,
    )
