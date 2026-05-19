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
    # Add manifest itself
    manifest["manifest.json"] = hashlib.sha256(
        (pkg_dir / "manifest.json").read_bytes()
    ).hexdigest()
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
