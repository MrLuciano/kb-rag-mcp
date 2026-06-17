"""
Tests for Phase 34: Upload/Index Quotas.

Covers MetadataStore quota helpers, ingest enforcement, and CLI.
"""

import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from ingest.cli.main import cli
from ingest.core.metadata import MetadataStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_db(tmp_path: Path) -> MetadataStore:
    """Create a fresh MetadataStore with schema v4 for testing."""
    db_path = tmp_path / "test_quotas.db"
    store = MetadataStore(db_path)
    store.connect()
    yield store
    store.close()


# ---------------------------------------------------------------------------
# MetadataStore quota helpers
# ---------------------------------------------------------------------------


class TestQuotaPersistence:
    """Quota config and usage table operations."""

    def test_quotas_default_to_empty(self, temp_db: MetadataStore) -> None:
        quotas = temp_db.get_quotas()
        assert isinstance(quotas, dict)
        # All limit columns exist and are None (unlimited)
        for col in (
            "max_files_per_upload",
            "max_bytes_per_upload",
            "max_bytes_per_file",
            "max_documents_per_index",
            "max_chunks_per_index",
            "max_chars_per_index",
        ):
            assert quotas.get(col) is None, f"{col} should be None"

    def test_set_and_get_quotas(self, temp_db: MetadataStore) -> None:
        temp_db.set_quotas(
            max_files_per_upload=10,
            max_bytes_per_upload=1_000_000,
            max_bytes_per_file=500_000,
            max_documents_per_index=1000,
            max_chunks_per_index=50000,
            max_chars_per_index=10_000_000,
        )
        quotas = temp_db.get_quotas()
        assert quotas["max_files_per_upload"] == 10
        assert quotas["max_bytes_per_upload"] == 1_000_000
        assert quotas["max_bytes_per_file"] == 500_000
        assert quotas["max_documents_per_index"] == 1000
        assert quotas["max_chunks_per_index"] == 50000
        assert quotas["max_chars_per_index"] == 10_000_000

    def test_set_partial_quotas(self, temp_db: MetadataStore) -> None:
        temp_db.set_quotas(max_files_per_upload=5)
        quotas = temp_db.get_quotas()
        assert quotas["max_files_per_upload"] == 5
        # Others remain None
        assert quotas["max_bytes_per_upload"] is None

    def test_usage_starts_at_zero(self, temp_db: MetadataStore) -> None:
        usage = temp_db.get_quota_usage()
        assert usage["total_files"] == 0
        assert usage["total_bytes"] == 0
        assert usage["total_documents"] == 0
        assert usage["total_chunks"] == 0
        assert usage["total_chars"] == 0


class TestQuotaCheck:
    """Quota enforcement logic."""

    def test_unlimited_always_passes(self, temp_db: MetadataStore) -> None:
        ok, msg = temp_db.check_quota(files_count=999, bytes_total=999_999_999)
        assert ok is True
        assert msg == ""

    def test_rejects_excessive_files(self, temp_db: MetadataStore) -> None:
        temp_db.set_quotas(max_files_per_upload=5)
        ok, msg = temp_db.check_quota(files_count=10, bytes_total=100)
        assert ok is False
        assert "max files" in msg.lower()

    def test_rejects_excessive_bytes(self, temp_db: MetadataStore) -> None:
        temp_db.set_quotas(max_bytes_per_upload=1000)
        ok, msg = temp_db.check_quota(files_count=1, bytes_total=2000)
        assert ok is False
        assert "max bytes" in msg.lower()

    def test_rejects_overly_large_file(self, temp_db: MetadataStore) -> None:
        temp_db.set_quotas(max_bytes_per_file=500)
        ok, msg = temp_db.check_quota(file_bytes=1000)
        assert ok is False
        assert "max bytes per file" in msg.lower()

    def test_rejects_excessive_documents(self, temp_db: MetadataStore) -> None:
        temp_db.set_quotas(max_documents_per_index=100)
        # Simulate existing usage at capacity
        temp_db.update_quota_usage(documents=100)
        ok, msg = temp_db.check_quota(files_count=1)
        assert ok is False
        assert "max documents" in msg.lower()

    def test_rejects_excessive_chunks(self, temp_db: MetadataStore) -> None:
        temp_db.set_quotas(max_chunks_per_index=1000)
        temp_db.update_quota_usage(chunks=1000)
        ok, msg = temp_db.check_quota()
        assert ok is False
        assert "max chunks" in msg.lower()

    def test_rejects_excessive_chars(self, temp_db: MetadataStore) -> None:
        temp_db.set_quotas(max_chars_per_index=5000)
        temp_db.update_quota_usage(chars=5000)
        ok, msg = temp_db.check_quota()
        assert ok is False
        assert "max character" in msg.lower() or "max char" in msg.lower()

    def test_accepts_when_under_limit(self, temp_db: MetadataStore) -> None:
        temp_db.set_quotas(
            max_files_per_upload=10,
            max_bytes_per_upload=10_000,
            max_documents_per_index=100,
            max_chunks_per_index=5000,
            max_chars_per_index=100_000,
        )
        temp_db.update_quota_usage(documents=50, chunks=2000, chars=40_000)
        ok, msg = temp_db.check_quota(files_count=5, bytes_total=5000)
        assert ok is True
        assert msg == ""


class TestQuotaUsage:
    """Usage counter updates."""

    def test_update_usage(self, temp_db: MetadataStore) -> None:
        temp_db.update_quota_usage(
            files=2, bytes_count=15000, documents=2, chunks=40, chars=20000
        )
        usage = temp_db.get_quota_usage()
        assert usage["total_files"] == 2
        assert usage["total_bytes"] == 15000
        assert usage["total_documents"] == 2
        assert usage["total_chunks"] == 40
        assert usage["total_chars"] == 20000

    def test_update_cumulative(self, temp_db: MetadataStore) -> None:
        temp_db.update_quota_usage(files=1, chunks=10)
        temp_db.update_quota_usage(files=2, chunks=20)
        usage = temp_db.get_quota_usage()
        assert usage["total_files"] == 3
        assert usage["total_chunks"] == 30

    def test_reset_usage(self, temp_db: MetadataStore) -> None:
        temp_db.update_quota_usage(files=5, chunks=100)
        prev = temp_db.reset_quota_usage()
        assert prev["total_files"] == 5
        usage = temp_db.get_quota_usage()
        assert usage["total_files"] == 0
        assert usage["total_chunks"] == 0


class TestQuotaSchemaMigration:
    """Verify migration path from no-quota DB (schema v3)."""

    def test_migration_adds_quota_tables(self, tmp_path: Path) -> None:
        """Create a DB at schema v3, then open again to trigger v4."""
        db_path = tmp_path / "migrate_test.db"
        # First open — schema v3 (no quota tables yet)
        store = MetadataStore(db_path)
        store.connect()
        # Manually set schema to 3 (skip quota migration)
        store._set_schema_version(3)
        store.close()

        # Re-open — should migrate from 3 to 4
        store2 = MetadataStore(db_path)
        store2.connect()
        # Verify quota tables exist
        tables = [
            r[0]
            for r in store2.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "quota_config" in tables
        assert "quota_usage" in tables
        assert store2._get_schema_version() == 5
        store2.close()


# ---------------------------------------------------------------------------
# Ingest enforcement integration
# ---------------------------------------------------------------------------


class TestIngestQuotaEnforcement:
    """run_ingest should reject when quota is exceeded."""

    def test_raises_on_quota_violation(self) -> None:
        from ingest.ingest import run_ingest
        import asyncio

        with (
            patch("ingest.core.metadata.MetadataStore") as mock_mds_cls,
            patch("kb_server.vector_store.VectorStore") as mock_vs_cls,
        ):
            mock_mds = mock_mds_cls.return_value
            mock_mds.check_quota.return_value = (False, "Too many files")
            mock_vs = mock_vs_cls.return_value
            mock_vs.connect = AsyncMock()

            with pytest.raises(RuntimeError, match="Too many files"):
                asyncio.run(
                    run_ingest(
                        docs_path=Path("/nonexistent"),
                        product="test",
                    )
                )

            mock_mds.check_quota.assert_called_once()


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class TestQuotaCLI:
    """Click CLI for quota management."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_quota_group_registered(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["quota", "--help"])
        assert result.exit_code == 0
        assert "Manage upload/index quotas" in result.output

    def test_quota_show(self, runner: CliRunner, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        with MetadataStore(db_path) as store:
            store.get_stats()  # ensure DB is initialized
        result = runner.invoke(cli, ["--db", str(db_path), "quota", "show"])
        assert result.exit_code == 0
        assert "Upload / Index Quotas" in result.output
        assert "Current Usage" in result.output

    def test_quota_set(self, runner: CliRunner, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        with MetadataStore(db_path):
            pass  # ensures DB is created and schema initialized
        result = runner.invoke(
            cli,
            [
                "--db",
                str(db_path),
                "quota",
                "set",
                "--max-chunks-per-index",
                "50000",
                "--max-documents-per-index",
                "1000",
            ],
        )
        assert result.exit_code == 0
        assert "Quotas updated" in result.output

        # Verify the values persisted
        store = MetadataStore(db_path)
        store.connect()
        quotas = store.get_quotas()
        store.close()
        assert quotas["max_chunks_per_index"] == 50000
        assert quotas["max_documents_per_index"] == 1000

    def test_quota_reset(self, runner: CliRunner, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        store = MetadataStore(db_path)
        store.connect()
        store.update_quota_usage(chunks=999)
        store.close()

        result = runner.invoke(
            cli,
            ["--db", str(db_path), "quota", "reset"],
            input="y\n",
        )
        assert result.exit_code == 0
        assert "Usage reset" in result.output

        store2 = MetadataStore(db_path)
        store2.connect()
        usage = store2.get_quota_usage()
        store2.close()
        assert usage["total_chunks"] == 0
