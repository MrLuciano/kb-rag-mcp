# tests/test_migration.py
import hashlib
import json
import tarfile
import tempfile
from pathlib import Path

import pytest


def _make_fake_package(tmp_path: Path) -> Path:
    """Create a minimal valid .tar.gz migration package for testing."""
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    # Create fake files
    (pkg_dir / "kb_metadata.db").write_bytes(b"SQLite fake")
    (pkg_dir / "qdrant_snapshot.snapshot").write_bytes(b"qdrant fake")
    # SHA256 manifest
    manifest = {}
    for f in pkg_dir.iterdir():
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        manifest[f.name] = digest
    (pkg_dir / "manifest.json").write_text(json.dumps(manifest))

    pkg_path = tmp_path / "test.tar.gz"
    with tarfile.open(pkg_path, "w:gz") as tar:
        for f in pkg_dir.iterdir():
            tar.add(f, arcname=f.name)
    return pkg_path


def test_validate_valid_package(tmp_path):
    from scripts.migrate.validate import validate_package
    pkg = _make_fake_package(tmp_path)
    result = validate_package(pkg)
    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_missing_manifest(tmp_path):
    from scripts.migrate.validate import validate_package
    pkg_path = tmp_path / "bad.tar.gz"
    with tarfile.open(pkg_path, "w:gz") as tar:
        f = tmp_path / "kb_metadata.db"
        f.write_bytes(b"data")
        tar.add(f, arcname="kb_metadata.db")
    result = validate_package(pkg_path)
    assert result["valid"] is False
    assert any("manifest" in e for e in result["errors"])


def test_validate_corrupted_file(tmp_path):
    from scripts.migrate.validate import validate_package
    pkg = _make_fake_package(tmp_path)
    # Tamper: rewrite with corrupted content
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    with tarfile.open(pkg, "r:gz") as tar:
        tar.extractall(extract_dir)
    (extract_dir / "kb_metadata.db").write_bytes(b"corrupted!")
    tampered = tmp_path / "tampered.tar.gz"
    with tarfile.open(tampered, "w:gz") as tar:
        for f in extract_dir.iterdir():
            tar.add(f, arcname=f.name)
    result = validate_package(tampered)
    assert result["valid"] is False
    assert any("kb_metadata.db" in e for e in result["errors"])


def test_export_creates_valid_package(tmp_path, monkeypatch):
    """Export with a fake Qdrant snapshot produces a valid package."""
    from scripts.migrate.export import export_kb

    # Fake SQLite DBs
    meta_db = tmp_path / "kb_metadata.db"
    meta_db.write_bytes(b"SQLite metadata")
    reg_db = tmp_path / "registry.db"
    reg_db.write_bytes(b"SQLite registry")

    # Mock Qdrant snapshot to just write a fake file
    def fake_snapshot(qdrant_url, collection, out_dir):
        snap = Path(out_dir) / "snapshot.snapshot"
        snap.write_bytes(b"qdrant snapshot data")
        return snap

    monkeypatch.setattr("scripts.migrate.export._take_qdrant_snapshot", fake_snapshot)

    out_pkg = tmp_path / "export.tar.gz"
    export_kb(
        output=out_pkg,
        metadata_db=meta_db,
        registry_db=reg_db,
        qdrant_url="http://localhost:6333",
        collection="kb_docs",
    )

    assert out_pkg.exists()
    from scripts.migrate.validate import validate_package
    result = validate_package(out_pkg)
    assert result["valid"] is True
    assert "manifest.json" in result["files"]


def test_export_includes_env_template(tmp_path, monkeypatch):
    """Export includes a sanitized env template."""
    from scripts.migrate.export import export_kb

    meta_db = tmp_path / "kb_metadata.db"
    meta_db.write_bytes(b"data")

    def fake_snapshot(qdrant_url, collection, out_dir):
        snap = Path(out_dir) / "snapshot.snapshot"
        snap.write_bytes(b"snap")
        return snap

    monkeypatch.setattr("scripts.migrate.export._take_qdrant_snapshot", fake_snapshot)

    # Create a fake .env file in tmp_path
    env_file = tmp_path / ".env"
    env_file.write_text("LMS_BASE_URL=http://192.168.1.177:1234\nQDRANT_COLLECTION=kb_docs\n")

    out_pkg = tmp_path / "export.tar.gz"
    export_kb(
        output=out_pkg,
        metadata_db=meta_db,
        qdrant_url="http://localhost:6333",
        collection="kb_docs",
        env_file=env_file,
    )

    import tarfile as tf
    with tf.open(out_pkg, "r:gz") as tar:
        names = tar.getnames()
    assert "env.template" in names
