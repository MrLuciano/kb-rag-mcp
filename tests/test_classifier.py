"""Unit tests for ingest/classifier.py — auto-tagging heuristics."""

from pathlib import Path

import pytest

from ingest.classifier import (
    DOC_TYPE_RULES,
    PRODUCT_ALIASES,
    PRODUCT_FROM_NAME,
    classify,
    classify_document,
    infer_doc_type,
    infer_product,
)


class TestInferDocType:
    def test_admin_guide(self):
        assert infer_doc_type(Path("Content-Server-Admin-Guide.pdf")) == "admin_guide"

    def test_standard_iso(self):
        assert infer_doc_type(Path("ISO-9001-Standard.pdf")) == "standard"

    def test_training(self):
        assert infer_doc_type(Path("Training-Manual-v2.pdf")) == "training"

    def test_release_notes(self):
        assert infer_doc_type(Path("Release-Notes-23.4.pdf")) == "release_notes"

    def test_install_guide(self):
        assert infer_doc_type(Path("Installation-Guide.pdf")) == "install_guide"

    def test_user_guide(self):
        assert infer_doc_type(Path("User-Guide.pdf")) == "user_guide"

    def test_api_guide(self):
        assert infer_doc_type(Path("API-Reference.pdf")) == "api_guide"

    def test_howto(self):
        assert infer_doc_type(Path("Troubleshooting-Guide.pdf")) == "howto"

    def test_reference(self):
        assert infer_doc_type(Path("Technical-Reference.pdf")) == "reference"

    def test_file_without_recognized_doc_type(self):
        assert infer_doc_type(Path("README.txt")) == "document"

    def test_zip_is_release_artifact(self):
        assert infer_doc_type(Path("some-package.zip")) == "release_artifact"

    def test_empty_path_does_not_crash(self):
        result = infer_doc_type(Path(""))
        assert isinstance(result, str)

    def test_case_insensitive_matching(self):
        assert infer_doc_type(Path("ADMIN-GUIDE.PDF")) == "admin_guide"


class TestInferProduct:
    def test_product_from_directory_name(self, tmp_path):
        docs_root = tmp_path / "docs"
        file_path = docs_root / "ContentServer" / "admin.pdf"
        docs_root.mkdir()
        (docs_root / "ContentServer").mkdir()
        (docs_root / "ContentServer" / "admin.pdf").write_text("")
        assert infer_product(file_path, docs_root) == "ContentServer"

    def test_product_from_override(self, tmp_path):
        file_path = tmp_path / "file.pdf"
        assert (
            infer_product(file_path, tmp_path, product_override="xECM")
            == "xECM"
        )

    def test_product_from_alias(self, tmp_path):
        docs_root = tmp_path / "docs"
        file_path = docs_root / "appserver" / "admin.pdf"
        docs_root.mkdir()
        (docs_root / "appserver").mkdir()
        (docs_root / "appserver" / "admin.pdf").write_text("")
        assert infer_product(file_path, docs_root) == "AppServer"

    def test_product_from_filename(self, tmp_path):
        docs_root = tmp_path / "docs"
        file_path = docs_root / "data-sync-config.pdf"
        docs_root.mkdir()
        (docs_root / "data-sync-config.pdf").write_text("")
        product = infer_product(file_path, docs_root)
        assert product == "DataSync"

    def test_product_fallback_geral(self, tmp_path):
        docs_root = tmp_path / "docs"
        file_path = docs_root / "varios" / "misc.pdf"
        docs_root.mkdir()
        (docs_root / "varios").mkdir()
        (docs_root / "varios" / "misc.pdf").write_text("")
        assert infer_product(file_path, docs_root) == "geral"

    def test_product_not_in_alias_uses_dir_name(self, tmp_path):
        docs_root = tmp_path / "docs"
        file_path = docs_root / "CustomProduct" / "file.pdf"
        docs_root.mkdir()
        (docs_root / "CustomProduct").mkdir()
        (docs_root / "CustomProduct" / "file.pdf").write_text("")
        assert infer_product(file_path, docs_root) == "CustomProduct"


class TestClassify:
    def test_classify_basic(self, tmp_path):
        docs_root = tmp_path / "docs"
        product_dir = docs_root / "ContentServer"
        product_dir.mkdir(parents=True)
        file_path = product_dir / "Admin-Guide-23.4.pdf"
        file_path.write_text("")
        result = classify(file_path, docs_root)
        assert result["product"] == "ContentServer"
        assert result["doc_type"] == "admin_guide"

    def test_classify_with_override(self, tmp_path):
        file_path = tmp_path / "file.pdf"
        result = classify(file_path, tmp_path, product_override="xECM")
        assert result["product"] == "xECM"

    def test_classify_document_wrapper(self, tmp_path):
        file_path = tmp_path / "Training-Material.pdf"
        result = classify_document(file_path)
        assert result["doc_type"] == "training"

    def test_classify_no_crash_with_unknown_file(self, tmp_path):
        file_path = tmp_path / "random_notes.txt"
        result = classify(file_path, tmp_path)
        assert isinstance(result, dict)
        assert "product" in result and "doc_type" in result


class TestModuleConstants:
    def test_doc_type_rules_are_well_formed(self):
        for priority, doc_type, patterns in DOC_TYPE_RULES:
            assert isinstance(priority, int)
            assert isinstance(doc_type, str)
            assert isinstance(patterns, list)
            assert len(patterns) >= 1

    def test_product_aliases_are_strings(self):
        for alias, product in PRODUCT_ALIASES.items():
            assert isinstance(alias, str)
            assert isinstance(product, str)

    def test_product_from_name_is_well_formed(self):
        for product, patterns in PRODUCT_FROM_NAME:
            assert isinstance(product, str)
            assert isinstance(patterns, list)
            assert len(patterns) >= 1
