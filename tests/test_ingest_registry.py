import tempfile
from pathlib import Path

from ingest.registry import IngestRegistry


def test_registry_init_and_context():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        reg = IngestRegistry(db_path)
        with reg:
            assert reg._conn is not None
        # After context exit, connection should be closed
        assert reg._conn is None
