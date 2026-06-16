# tests/test_zip_handler.py
import zipfile
from pathlib import Path

import pytest


def _make_zip(tmp_path: Path, files: dict, zip_name: str = "test.zip") -> Path:
    """Create a zip file with given filename→content mapping."""
    zip_path = tmp_path / zip_name
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return zip_path


def test_extract_zip_returns_list_of_dicts(tmp_path):
    """ZIP with a .txt file returns extracted text."""
    from ingest.parsers.zip_handler import extract_zip

    zip_path = _make_zip(tmp_path, {"hello.txt": b"Hello from zip"})
    result = extract_zip(zip_path)
    assert isinstance(result, list)
    assert len(result) > 0
    assert any("Hello from zip" in r["text"] for r in result)


def test_extract_zip_nested_one_level(tmp_path):
    """ZIP containing a ZIP (1 level deep) extracts inner files."""
    from ingest.parsers.zip_handler import extract_zip

    inner_zip_path = tmp_path / "inner.zip"
    with zipfile.ZipFile(inner_zip_path, "w") as zf:
        zf.writestr("inner.txt", "Inner content")

    outer_zip_path = _make_zip(
        tmp_path,
        {
            "inner.zip": inner_zip_path.read_bytes(),
            "outer.txt": b"Outer content",
        },
        "outer.zip",
    )

    result = extract_zip(outer_zip_path)
    texts = [r["text"] for r in result]
    assert any("Inner content" in t for t in texts)
    assert any("Outer content" in t for t in texts)


def test_extract_zip_skips_unsupported_types(tmp_path):
    """ZIP with .exe files skips them and does not return exe content."""
    from ingest.parsers.zip_handler import extract_zip

    zip_path = _make_zip(
        tmp_path,
        {
            "readme.txt": b"Read me",
            "binary.exe": b"\x4d\x5a binary data",
        },
    )
    result = extract_zip(zip_path)
    assert any("Read me" in r["text"] for r in result)
    assert not any(b"\x4d\x5a" in r.get("text", "").encode() for r in result)


def test_extract_zip_max_depth_two(tmp_path):
    """ZIPs nested deeper than 2 levels are not extracted."""
    from ingest.parsers.zip_handler import extract_zip

    # Level 3 (deepest — should NOT be extracted)
    l3 = tmp_path / "l3.zip"
    with zipfile.ZipFile(l3, "w") as zf:
        zf.writestr("deep.txt", "Too deep content")

    # Level 2
    l2 = tmp_path / "l2.zip"
    with zipfile.ZipFile(l2, "w") as zf:
        zf.writestr("l3.zip", l3.read_bytes())

    # Level 1 (what we call extract_zip on)
    l1 = tmp_path / "l1.zip"
    with zipfile.ZipFile(l1, "w") as zf:
        zf.writestr("l2.zip", l2.read_bytes())

    result = extract_zip(l1)
    texts = " ".join(r["text"] for r in result)
    assert "Too deep content" not in texts


def test_extract_zip_missing_file_returns_empty(tmp_path):
    from ingest.parsers.zip_handler import extract_zip

    result = extract_zip(tmp_path / "nonexistent.zip")
    assert result == []
