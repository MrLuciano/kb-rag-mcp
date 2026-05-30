"""
E2E tests for ingestion workflow using actual ingest/core/metadata API.

Tests end-to-end document ingestion using the real MetadataStore and
IngestRegistry classes.
"""

import os
import sqlite3
import tempfile
from pathlib import Path
import pytest


class TestIngestionWorkflow:
    """Test ingestion workflow using MetadataStore and IngestRegistry."""

    def test_ingest_single_text_file(
        self,
        e2e_test_docs_dir: Path,
        e2e_temp_registry: Path,
        tmp_path: Path,
    ):
        """Test ingesting a single text file into registry."""
        from ingest.core.metadata import IngestRegistry

        registry = IngestRegistry(e2e_temp_registry)
        registry.connect()

        # Get test file
        test_file = e2e_test_docs_dir / "test.txt"
        assert test_file.exists()

        # Mark as successfully ingested
        registry.mark_ok(
            path=test_file,
            rel_path=str(test_file.relative_to(e2e_test_docs_dir)),
            chunks=3,
            file_type="txt",
            product="general",
            doc_type="document",
        )

        # Verify registration
        record = registry.get_record(str(test_file.relative_to(e2e_test_docs_dir)))
        assert record is not None
        assert record["status"] == "ok"
        assert record["chunks"] == 3
        assert record["product"] == "general"

        registry.close()

    def test_ingest_directory_with_classification(
        self,
        e2e_test_docs_dir: Path,
        e2e_temp_registry: Path,
    ):
        """Test ingesting directory with automatic product classification."""
        from ingest.core.metadata import IngestRegistry
        from ingest.classifier import classify

        registry = IngestRegistry(e2e_temp_registry)
        registry.connect()

        # Test product directory
        product_dir = e2e_test_docs_dir / "TestProduct"
        test_file = product_dir / "manual.txt"

        # Classify product
        result = classify(test_file, docs_root=test_file.parent)
        product = result.get("product", "geral")

        # Register with classification
        registry.mark_ok(
            path=test_file,
            rel_path=str(test_file.relative_to(e2e_test_docs_dir)),
            chunks=5,
            file_type="txt",
            product=product,
            doc_type=result.get("doc_type", "document"),
        )

        # Verify product classification
        record = registry.get_record(
            str(test_file.relative_to(e2e_test_docs_dir))
        )
        assert record is not None
        assert record["product"] == product

        registry.close()

    def test_incremental_ingestion(
        self,
        e2e_test_docs_dir: Path,
        e2e_temp_registry: Path,
    ):
        """Test incremental ingestion only processes new/modified files."""
        from ingest.core.metadata import IngestRegistry

        registry = IngestRegistry(e2e_temp_registry)
        registry.connect()

        test_file = e2e_test_docs_dir / "test.txt"

        # First ingestion
        registry.mark_ok(
            path=test_file,
            rel_path=str(test_file.relative_to(e2e_test_docs_dir)),
            chunks=2,
            file_type="txt",
            product="general",
            doc_type="document",
        )

        # Verify file registered
        assert registry.is_indexed(
            str(test_file.relative_to(e2e_test_docs_dir))
        )

        # Modify file
        original_content = test_file.read_text()
        test_file.write_text("Modified content for testing")

        # Check needs_ingest detects modification
        needs, reason = registry.needs_ingest(
            test_file,
            str(test_file.relative_to(e2e_test_docs_dir)),
        )
        assert needs is True
        assert "modified" in reason

        # Restore original content
        test_file.write_text(original_content)

        registry.close()

    def test_ingestion_error_handling(
        self,
        e2e_temp_registry: Path,
        tmp_path: Path,
    ):
        """Test error handling during ingestion."""
        from ingest.core.metadata import IngestRegistry

        registry = IngestRegistry(e2e_temp_registry)
        registry.connect()

        # Simulate file that doesn't exist
        fake_file = tmp_path / "nonexistent.txt"

        registry.mark_error(
            path=fake_file,
            rel_path="nonexistent.txt",
            error="File not found",
            file_type="txt",
            product="test",
            doc_type="document",
        )

        # Verify error recorded
        record = registry.get_record("nonexistent.txt")
        assert record is not None
        assert record["status"] == "error"
        assert "File not found" in record["error_msg"]

        registry.close()


class TestIngestionStats:
    """Test ingestion statistics and status reporting."""

    def test_ingestion_status_summary(
        self,
        e2e_test_docs_dir: Path,
        e2e_temp_registry: Path,
    ):
        """Test ingestion status summary."""
        from ingest.core.metadata import IngestRegistry

        registry = IngestRegistry(e2e_temp_registry)
        registry.connect()

        # Register multiple files with different statuses
        files = [
            (e2e_test_docs_dir / "test.txt", "ok"),
            (e2e_test_docs_dir / "README.md", "ok"),
            (e2e_test_docs_dir / "TestProduct" / "manual.txt", "error"),
        ]

        for i, (file_path, status) in enumerate(files):
            if status == "ok":
                registry.mark_ok(
                    path=file_path,
                    rel_path=str(file_path.relative_to(e2e_test_docs_dir)),
                    chunks=i + 1,
                    file_type="txt",
                    product="test",
                    doc_type="document",
                )
            else:
                registry.mark_error(
                    path=file_path,
                    rel_path=str(file_path.relative_to(e2e_test_docs_dir)),
                    error="Simulated error",
                    file_type="txt",
                    product="test",
                    doc_type="document",
                )

        # Get stats
        stats = registry.summary()
        assert stats["ok"] == 2
        assert stats["errors"] == 1

        registry.close()

    def test_list_files_by_product(
        self,
        e2e_test_docs_dir: Path,
        e2e_temp_registry: Path,
    ):
        """Test listing files by product."""
        from ingest.core.metadata import IngestRegistry

        registry = IngestRegistry(e2e_temp_registry)
        registry.connect()

        # Register files for different products
        registry.mark_ok(
            path=e2e_test_docs_dir / "test.txt",
            rel_path="test.txt",
            chunks=2,
            file_type="txt",
            product="ProductA",
            doc_type="document",
        )

        registry.mark_ok(
            path=e2e_test_docs_dir / "README.md",
            rel_path="README.md",
            chunks=3,
            file_type="md",
            product="ProductB",
            doc_type="document",
        )

        # Query by product
        results = registry.list_all(status="ok")
        product_a = [r for r in results if r["product"] == "ProductA"]
        product_b = [r for r in results if r["product"] == "ProductB"]

        assert len(product_a) == 1
        assert len(product_b) == 1
        assert product_a[0]["path"] == "test.txt"

        registry.close()


@pytest.mark.skipif(
    os.getenv("SKIP_INTEGRATION_TESTS") == "1",
    reason="Integration tests disabled"
)
class TestRealIngestion:
    """
    Integration tests with real embedding and vector store.

    Requires:
    - LM Studio or Ollama running
    - Qdrant running
    - Set SKIP_INTEGRATION_TESTS=0 to enable
    """

    @pytest.mark.asyncio
    async def test_real_embedding_generation(self):
        """Test with real embedding service."""
        pytest.skip("Requires external embedding service")

    @pytest.mark.asyncio
    async def test_real_vector_store_insertion(self):
        """Test with real Qdrant instance."""
        pytest.skip("Requires Qdrant running")
