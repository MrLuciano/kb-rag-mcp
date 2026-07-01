import tempfile
from pathlib import Path

from ingest.core.metadata import IngestRegistry, MetadataStore


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
        assert reg.is_indexed(
            rel, checksum=sha_a
        ), "should be indexed with same checksum (dedup)"
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

        assert not reg.is_indexed(
            rel, checksum=sha_b
        ), "different checksum must not match as indexed"
        reg.close()


class TestConnectorState:
    """Tests for connector state persistence in MetadataStore."""

    def test_connector_state_round_trip(self, tmp_path):
        """Connector state can be persisted and retrieved."""
        db = tmp_path / "test_conn.db"
        store = MetadataStore(db_path=db)
        store.connect()

        store.upsert_connector_state(
            source_key="confluence://myspace",
            remote_id="page-123",
            connector_type="confluence",
            sync_checkpoint="cursor_abc",
            remote_etag='"etag-1"',
            remote_mtime=1000.0,
            local_path="/tmp/staged/page-123.md",
        )

        state = store.get_connector_state("confluence://myspace", "page-123")
        assert state is not None
        assert state["source_key"] == "confluence://myspace"
        assert state["remote_id"] == "page-123"
        assert state["connector_type"] == "confluence"
        assert state["sync_checkpoint"] == "cursor_abc"
        assert state["remote_etag"] == '"etag-1"'
        assert state["remote_mtime"] == 1000.0
        assert state["local_path"] == "/tmp/staged/page-123.md"
        assert state["status"] == "ok"

        store.close()

    def test_connector_state_update(self, tmp_path):
        """Updating existing connector state preserves source_key/remote_id."""
        db = tmp_path / "test_conn_update.db"
        store = MetadataStore(db_path=db)
        store.connect()

        store.upsert_connector_state(
            source_key="jira://PROJ",
            remote_id="PROJ-42",
            connector_type="jira",
            sync_checkpoint="cursor_v1",
        )

        store.upsert_connector_state(
            source_key="jira://PROJ",
            remote_id="PROJ-42",
            connector_type="jira",
            sync_checkpoint="cursor_v2",
            remote_etag='"new-etag"',
        )

        state = store.get_connector_state("jira://PROJ", "PROJ-42")
        assert state is not None
        assert state["sync_checkpoint"] == "cursor_v2"
        assert state["remote_etag"] == '"new-etag"'

        store.close()

    def test_connector_state_not_found(self, tmp_path):
        """Getting state for non-existent key returns None."""
        db = tmp_path / "test_conn_nf.db"
        store = MetadataStore(db_path=db)
        store.connect()

        state = store.get_connector_state("confluence://nope", "page-999")
        assert state is None

        store.close()

    def test_list_connector_state_filter(self, tmp_path):
        """List connector state with filters works correctly."""
        db = tmp_path / "test_conn_list.db"
        store = MetadataStore(db_path=db)
        store.connect()

        store.upsert_connector_state(
            source_key="confluence://space1",
            remote_id="page-1",
            connector_type="confluence",
        )
        store.upsert_connector_state(
            source_key="confluence://space1",
            remote_id="page-2",
            connector_type="confluence",
        )
        store.upsert_connector_state(
            source_key="jira://PROJ",
            remote_id="PROJ-1",
            connector_type="jira",
        )

        all_states = store.list_connector_state()
        assert len(all_states) == 3

        confluence_states = store.list_connector_state(
            connector_type="confluence"
        )
        assert len(confluence_states) == 2

        jira_states = store.list_connector_state(connector_type="jira")
        assert len(jira_states) == 1

        store.close()

    def test_delete_connector_state(self, tmp_path):
        """Deleting connector state removes the record."""
        db = tmp_path / "test_conn_del.db"
        store = MetadataStore(db_path=db)
        store.connect()

        store.upsert_connector_state(
            source_key="confluence://space",
            remote_id="page-to-delete",
            connector_type="confluence",
        )
        assert (
            store.get_connector_state("confluence://space", "page-to-delete")
            is not None
        )

        store.delete_connector_state("confluence://space", "page-to-delete")
        assert (
            store.get_connector_state("confluence://space", "page-to-delete")
            is None
        )

        store.close()

    def test_get_connector_sync_checkpoint(self, tmp_path):
        """Checkpoint retrieval returns latest cursor."""
        db = tmp_path / "test_conn_ck.db"
        store = MetadataStore(db_path=db)
        store.connect()

        checkpoint = store.get_connector_sync_checkpoint(
            "confluence://myspace"
        )
        assert checkpoint is None

        store.upsert_connector_state(
            source_key="confluence://myspace",
            remote_id="page-1",
            connector_type="confluence",
            sync_checkpoint="cursor_v1",
        )
        store.upsert_connector_state(
            source_key="confluence://myspace",
            remote_id="page-2",
            connector_type="confluence",
            sync_checkpoint="cursor_v2",
        )

        checkpoint = store.get_connector_sync_checkpoint(
            "confluence://myspace"
        )
        assert checkpoint in ("cursor_v1", "cursor_v2")

        store.close()

    def test_schema_migration_v3_on_fresh_db(self, tmp_path):
        """Fresh database gets v4 schema with connector_state and quota tables."""
        db = tmp_path / "test_v4_fresh.db"
        store = MetadataStore(db_path=db)
        store.connect()

        tables = [
            r[0]
            for r in store.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "connector_state" in tables
        assert "quota_config" in tables
        assert "quota_usage" in tables

        row = store.conn.execute(
            "SELECT version FROM schema_version"
        ).fetchone()
        assert row["version"] == 6

        store.close()

    def test_connector_schema_does_not_break_local_registry(self, tmp_path):
        """Connector state entries don't interfere with local file dedup/registry."""
        from ingest.core.metadata import IngestRegistry

        db = tmp_path / "test_conn_reg.db"

        # First, create connector_state entries via MetadataStore
        meta = MetadataStore(db_path=db)
        meta.connect()
        meta.upsert_connector_state(
            source_key="confluence://myspace",
            remote_id="page-123",
            connector_type="confluence",
            sync_checkpoint="cursor_v1",
        )
        meta.upsert_connector_state(
            source_key="jira://PROJ",
            remote_id="PROJ-42",
            connector_type="jira",
            sync_checkpoint="cursor_v2",
        )
        meta.close()

        # Now create IngestRegistry using same DB and verify local registry works
        reg = IngestRegistry(db_path=db)
        reg.connect()

        file_a = tmp_path / "doc_a.txt"
        file_a.write_text("identical content")
        file_b = tmp_path / "doc_b.txt"
        file_b.write_text("identical content")

        sha_a = IngestRegistry.sha256(file_a)
        sha_b = IngestRegistry.sha256(file_b)
        assert sha_a == sha_b, "identical files must have same sha256"

        # mark_indexed should still work
        reg.mark_indexed("docs/doc_a.txt", checksum=sha_a, chunks=3)
        assert reg.is_indexed("docs/doc_a.txt", checksum=sha_a)

        # needs_ingest for same content should say no changes
        needs, reason = reg.needs_ingest(file_a, "docs/doc_a.txt")
        assert not needs
        assert "no changes" in reason

        # needs_ingest for modified content should detect changes
        file_b.write_text("modified content")
        needs, reason = reg.needs_ingest(file_b, "docs/doc_b.txt")
        assert needs
        assert ("new" in reason or "modified" in reason)

        reg.close()

    def test_connector_state_migration_from_v2(self, tmp_path):
        """Existing v2 database upgrades to v3+ with connector_state without data loss."""
        db = tmp_path / "test_v2_to_v3.db"

        # 1. Create a v2 schema manually (tables that existed before v3)
        import sqlite3

        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE schema_version (version INTEGER NOT NULL);
            INSERT INTO schema_version (version) VALUES (2);

            CREATE TABLE jobs (
                job_id TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'pending',
                priority INTEGER NOT NULL DEFAULT 50, docs_path TEXT NOT NULL,
                product_override TEXT, workers INTEGER NOT NULL DEFAULT 2,
                clean INTEGER NOT NULL DEFAULT 0, force INTEGER NOT NULL DEFAULT 0,
                sync INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL,
                started_at REAL, completed_at REAL, error TEXT,
                total_files INTEGER DEFAULT 0, processed_files INTEGER DEFAULT 0,
                total_chunks INTEGER DEFAULT 0
            );

            CREATE TABLE files (
                path TEXT PRIMARY KEY, sha256 TEXT NOT NULL,
                file_type TEXT, product TEXT, doc_type TEXT DEFAULT 'document',
                chunks INTEGER DEFAULT 0, status TEXT DEFAULT 'ok',
                error_msg TEXT, indexed_at REAL NOT NULL,
                file_mtime REAL, file_size INTEGER, tags TEXT DEFAULT '[]'
            );

            CREATE TABLE job_progress (
                job_id TEXT NOT NULL, file_path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                chunks_generated INTEGER DEFAULT 0, error TEXT,
                started_at REAL, completed_at REAL,
                PRIMARY KEY (job_id, file_path),
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            );
        """)

        # 2. Insert sample local file entries
        conn.execute(
            "INSERT INTO files (path, sha256, file_type, product, chunks, status, indexed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("docs/manual.pdf", "aaa111", "pdf", "ProductX", 10, "ok", 1000.0),
        )
        conn.execute(
            "INSERT INTO files (path, sha256, file_type, product, chunks, status, indexed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("docs/readme.md", "bbb222", "txt", "ProductX", 3, "ok", 1001.0),
        )
        conn.execute(
            "INSERT INTO jobs (job_id, status, priority, docs_path, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("job-001", "completed", 50, "/docs", 1000.0),
        )
        conn.commit()
        conn.close()

        # 3. Now open with MetadataStore - it should migrate v2→v3→v4→v5→v6
        store = MetadataStore(db_path=db)
        store.connect()

        # 4. Verify schema version is now 6
        row = store.conn.execute(
            "SELECT version FROM schema_version"
        ).fetchone()
        assert row["version"] == 6, f"Expected schema v6, got v{row['version']}"

        # 5. Verify connector_state table exists
        tables = [
            r[0]
            for r in store.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "connector_state" in tables

        # 6. Verify local file entries are intact
        file_rows = store.conn.execute(
            "SELECT * FROM files ORDER BY path"
        ).fetchall()
        assert len(file_rows) == 2

        files_by_path = {r["path"]: r for r in file_rows}
        assert files_by_path["docs/manual.pdf"]["sha256"] == "aaa111"
        assert files_by_path["docs/manual.pdf"]["product"] == "ProductX"
        assert files_by_path["docs/manual.pdf"]["chunks"] == 10
        assert files_by_path["docs/readme.md"]["sha256"] == "bbb222"

        # 7. Verify jobs table entries are intact
        job_rows = store.conn.execute(
            "SELECT * FROM jobs"
        ).fetchall()
        assert len(job_rows) == 1
        assert job_rows[0]["job_id"] == "job-001"

        # 8. Verify quota tables also created
        assert "quota_config" in tables
        assert "quota_usage" in tables

        store.close()
