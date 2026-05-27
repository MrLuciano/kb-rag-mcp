"""Tests for cache-bust marker file writing."""

import tempfile
from pathlib import Path

from ingest.utils import write_filter_cache_bust


def test_write_cache_bust_marker():
    with tempfile.TemporaryDirectory() as tmpdir:
        marker_path = Path(tmpdir) / ".filter_cache_bust"
        write_filter_cache_bust(marker_path)
        assert marker_path.exists()
        content = marker_path.read_text().strip()
        assert len(content) > 0


def test_write_cache_bust_marker_creates_parent_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        marker_path = Path(tmpdir) / "subdir" / ".filter_cache_bust"
        write_filter_cache_bust(marker_path)
        assert marker_path.exists()
        content = marker_path.read_text().strip()
        assert len(content) > 0


def test_write_cache_bust_marker_default_path():
    write_filter_cache_bust(Path("/tmp/test_filter_cache_bust"))
    marker_path = Path("/tmp/test_filter_cache_bust")
    assert marker_path.exists()
    content = marker_path.read_text().strip()
    assert len(content) > 0
    marker_path.unlink()
