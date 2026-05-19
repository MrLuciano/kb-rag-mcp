import tempfile
from pathlib import Path

from ingest.core.metadata import IngestRegistry


def test_registry_init_and_context():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        reg = IngestRegistry(db_path)
        with reg:
            assert reg._conn is not None
        # After context exit, connection should be closed
        assert reg._conn is None


class TestIngestRegistryDedup:
    def test_deduplication_same_checksum(self, tmp_path):
        """Two files with identical content deduplicate correctly."""
        db = tmp_path / "test_registry.db"
        reg = IngestRegistry(db_path=db)
        reg.connect()

        file_a = tmp_path / "doc_a.txt"
        file_a.write_text("identical content")
        file_b = tmp_path / "doc_b.txt"
        file_b.write_text("identical content")

        sha_a = IngestRegistry.sha256(file_a)
        sha_b = IngestRegistry.sha256(file_b)
        assert sha_a == sha_b, "identical files must have same sha256"

        rel = "docs/doc_a.txt"
        assert not reg.is_indexed(rel, checksum=sha_a)
        reg.mark_indexed(rel, checksum=sha_a, chunks=3)
        assert reg.is_indexed(rel, checksum=sha_a), \
            "should be indexed with same checksum (dedup)"
        reg.close()

    def test_deduplication_different_checksum(self, tmp_path):
        """Two files with different content do NOT deduplicate."""
        db = tmp_path / "test_registry2.db"
        reg = IngestRegistry(db_path=db)
        reg.connect()

        file_a = tmp_path / "doc_a.txt"
        file_a.write_text("content version 1")
        file_b = tmp_path / "doc_b.txt"
        file_b.write_text("content version 2 — different")

        sha_a = IngestRegistry.sha256(file_a)
        sha_b = IngestRegistry.sha256(file_b)
        assert sha_a != sha_b

        rel = "docs/shared_path.txt"
        reg.mark_indexed(rel, checksum=sha_a, chunks=2)

        assert not reg.is_indexed(rel, checksum=sha_b), \
            "different checksum must not match as indexed"
        reg.close()
