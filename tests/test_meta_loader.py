"""
Tests for metadata loader.

Tests cover:
- Loading _meta.json files
- Schema validation (valid/invalid doc_types)
- Precedence (file-specific > directory > auto)
- Partial overrides
- Batch scanning
- Error handling
"""

import json
from pathlib import Path

import pytest

from ingest.core.meta_loader import (
    MetaLoader,
    get_file_metadata,
    load_directory_meta,
)


class TestMetaLoader:
    """Test metadata loading and precedence."""

    @pytest.fixture
    def loader(self):
        """Create loader instance."""
        return MetaLoader()

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory."""
        return tmp_path

    def test_load_meta_not_exists(self, loader, temp_dir):
        """Return empty dict when _meta.json doesn't exist."""
        meta = loader.load_meta(temp_dir)
        assert meta == {}

    def test_load_meta_valid(self, loader, temp_dir):
        """Load valid _meta.json."""
        meta_file = temp_dir / "_meta.json"
        meta_file.write_text(
            json.dumps({"product": "TestProduct", "doc_type": "admin_guide"})
        )

        meta = loader.load_meta(temp_dir)
        assert meta["product"] == "TestProduct"
        assert meta["doc_type"] == "admin_guide"

    def test_load_meta_with_file_overrides(self, loader, temp_dir):
        """Load _meta.json with file-specific overrides."""
        meta_file = temp_dir / "_meta.json"
        meta_file.write_text(
            json.dumps(
                {
                    "product": "DefaultProduct",
                    "doc_type": "admin_guide",
                    "files": {
                        "special.pdf": {
                            "product": "SpecialProduct",
                            "doc_type": "user_guide",
                        }
                    },
                }
            )
        )

        meta = loader.load_meta(temp_dir)
        assert meta["product"] == "DefaultProduct"
        assert "files" in meta
        assert "special.pdf" in meta["files"]

    def test_validate_invalid_doc_type(self, loader, temp_dir):
        """Reject invalid doc_type."""
        meta_file = temp_dir / "_meta.json"
        meta_file.write_text(json.dumps({"doc_type": "invalid_type"}))

        with pytest.raises(ValueError, match="Invalid doc_type"):
            loader.load_meta(temp_dir)

    def test_validate_invalid_file_doc_type(self, loader, temp_dir):
        """Reject invalid doc_type in file-specific override."""
        meta_file = temp_dir / "_meta.json"
        meta_file.write_text(
            json.dumps(
                {"files": {"test.pdf": {"doc_type": "invalid_type"}}}
            )
        )

        with pytest.raises(ValueError, match="Invalid doc_type"):
            loader.load_meta(temp_dir)

    def test_validate_invalid_json(self, loader, temp_dir):
        """Reject malformed JSON."""
        meta_file = temp_dir / "_meta.json"
        meta_file.write_text("{invalid json")

        with pytest.raises(ValueError, match="Invalid JSON"):
            loader.load_meta(temp_dir)

    def test_validate_files_not_dict(self, loader, temp_dir):
        """Reject when 'files' is not a dict."""
        meta_file = temp_dir / "_meta.json"
        meta_file.write_text(json.dumps({"files": ["not", "a", "dict"]}))

        with pytest.raises(ValueError, match="must be a dict"):
            loader.load_meta(temp_dir)

    def test_precedence_file_specific(self, loader):
        """File-specific override takes precedence."""
        meta = {
            "product": "DirProduct",
            "doc_type": "admin_guide",
            "files": {
                "test.pdf": {
                    "product": "FileProduct",
                    "doc_type": "user_guide",
                }
            },
        }

        file_path = Path("/docs/test.pdf")
        overrides = loader.get_metadata(file_path, meta)

        assert overrides["product"] == "FileProduct"
        assert overrides["doc_type"] == "user_guide"

    def test_precedence_directory_default(self, loader):
        """Directory default used when no file-specific."""
        meta = {"product": "DirProduct", "doc_type": "admin_guide"}

        file_path = Path("/docs/test.pdf")
        overrides = loader.get_metadata(file_path, meta)

        assert overrides["product"] == "DirProduct"
        assert overrides["doc_type"] == "admin_guide"

    def test_precedence_no_overrides(self, loader):
        """Return None values when no overrides."""
        meta = {}

        file_path = Path("/docs/test.pdf")
        overrides = loader.get_metadata(file_path, meta)

        assert overrides["product"] is None
        assert overrides["doc_type"] is None

    def test_partial_file_override_product_only(self, loader):
        """File can override product only, inherit doc_type."""
        meta = {
            "product": "DirProduct",
            "doc_type": "admin_guide",
            "files": {"test.pdf": {"product": "FileProduct"}},
        }

        file_path = Path("/docs/test.pdf")
        overrides = loader.get_metadata(file_path, meta)

        assert overrides["product"] == "FileProduct"
        assert overrides["doc_type"] == "admin_guide"

    def test_partial_file_override_doc_type_only(self, loader):
        """File can override doc_type only, inherit product."""
        meta = {
            "product": "DirProduct",
            "doc_type": "admin_guide",
            "files": {"test.pdf": {"doc_type": "user_guide"}},
        }

        file_path = Path("/docs/test.pdf")
        overrides = loader.get_metadata(file_path, meta)

        assert overrides["product"] == "DirProduct"
        assert overrides["doc_type"] == "user_guide"

    def test_scan_directory_finds_all(self, loader, temp_dir):
        """scan_directory() finds all _meta.json files."""
        # Create directory structure with multiple _meta.json files
        dir1 = temp_dir / "dir1"
        dir1.mkdir()
        (dir1 / "_meta.json").write_text(
            json.dumps({"product": "Product1"})
        )

        dir2 = temp_dir / "dir2"
        dir2.mkdir()
        (dir2 / "_meta.json").write_text(
            json.dumps({"product": "Product2"})
        )

        meta_map = loader.scan_directory(temp_dir)

        assert len(meta_map) == 2
        assert dir1 in meta_map
        assert dir2 in meta_map
        assert meta_map[dir1]["product"] == "Product1"
        assert meta_map[dir2]["product"] == "Product2"

    def test_scan_directory_nested(self, loader, temp_dir):
        """scan_directory() finds nested _meta.json files."""
        nested = temp_dir / "level1" / "level2"
        nested.mkdir(parents=True)
        (nested / "_meta.json").write_text(
            json.dumps({"product": "NestedProduct"})
        )

        meta_map = loader.scan_directory(temp_dir)

        assert len(meta_map) == 1
        assert nested in meta_map
        assert meta_map[nested]["product"] == "NestedProduct"

    def test_scan_directory_handles_errors(
        self, loader, temp_dir, caplog
    ):
        """scan_directory() logs errors but continues."""
        # Create one valid and one invalid _meta.json
        valid_dir = temp_dir / "valid"
        valid_dir.mkdir()
        (valid_dir / "_meta.json").write_text(
            json.dumps({"product": "Valid"})
        )

        invalid_dir = temp_dir / "invalid"
        invalid_dir.mkdir()
        (invalid_dir / "_meta.json").write_text("{invalid json")

        meta_map = loader.scan_directory(temp_dir)

        # Should load valid file despite error in other
        assert len(meta_map) == 1
        assert valid_dir in meta_map
        assert "Failed to load" in caplog.text

    def test_convenience_function_load(self, temp_dir):
        """Test convenience function for loading."""
        meta_file = temp_dir / "_meta.json"
        meta_file.write_text(
            json.dumps({"product": "TestProduct"})
        )

        meta = load_directory_meta(temp_dir)
        assert meta["product"] == "TestProduct"

    def test_convenience_function_get(self):
        """Test convenience function for getting metadata."""
        meta = {
            "product": "DirProduct",
            "files": {"test.pdf": {"product": "FileProduct"}},
        }

        file_path = Path("/docs/test.pdf")
        overrides = get_file_metadata(file_path, meta)

        assert overrides["product"] == "FileProduct"


class TestValidDocTypes:
    """Test doc_type validation against allowed list."""

    @pytest.fixture
    def loader(self):
        """Create loader instance."""
        return MetaLoader()

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory."""
        return tmp_path

    def test_all_valid_doc_types_accepted(self, loader, temp_dir):
        """All valid doc_types should be accepted."""
        valid_types = [
            "admin_guide",
            "install_guide",
            "upgrade_guide",
            "config_guide",
            "user_guide",
            "api_guide",
            "release_notes",
            "howto",
            "training",
            "overview",
            "reference",
            "standard",
            "meeting",
            "release_artifact",
            "document",
        ]

        for doc_type in valid_types:
            meta_file = temp_dir / "_meta.json"
            meta_file.write_text(json.dumps({"doc_type": doc_type}))

            # Should not raise error
            meta = loader.load_meta(temp_dir)
            assert meta["doc_type"] == doc_type

    def test_arbitrary_product_accepted(self, loader, temp_dir):
        """Any string should be accepted for product."""
        test_products = [
            "AppServer",
            "DataSync",
            "MyCustomProduct",
            "Product-With-Dashes",
            "Product123",
        ]

        for product in test_products:
            meta_file = temp_dir / "_meta.json"
            meta_file.write_text(json.dumps({"product": product}))

            # Should not raise error
            meta = loader.load_meta(temp_dir)
            assert meta["product"] == product


class TestMetaLoaderEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def loader(self):
        """Create loader instance."""
        return MetaLoader()

    def test_empty_meta_file(self, loader, tmp_path):
        """Empty _meta.json should be valid."""
        meta_file = tmp_path / "_meta.json"
        meta_file.write_text("{}")

        meta = loader.load_meta(tmp_path)
        assert meta == {}

    def test_meta_with_only_files(self, loader, tmp_path):
        """_meta.json with only files section should be valid."""
        meta_file = tmp_path / "_meta.json"
        meta_file.write_text(
            json.dumps({"files": {"test.pdf": {"product": "Test"}}})
        )

        meta = loader.load_meta(tmp_path)
        assert "files" in meta
        assert "test.pdf" in meta["files"]

    def test_file_not_in_overrides(self, loader):
        """File not in overrides should get directory defaults."""
        meta = {
            "product": "DirProduct",
            "files": {"other.pdf": {"product": "OtherProduct"}},
        }

        file_path = Path("/docs/test.pdf")
        overrides = loader.get_metadata(file_path, meta)

        assert overrides["product"] == "DirProduct"

    def test_unicode_in_metadata(self, loader, tmp_path):
        """Unicode characters should be handled correctly."""
        meta_file = tmp_path / "_meta.json"
        meta_file.write_text(
            json.dumps({"product": "Produção"}, ensure_ascii=False),
            encoding="utf-8",
        )

        meta = loader.load_meta(tmp_path)
        assert meta["product"] == "Produção"
