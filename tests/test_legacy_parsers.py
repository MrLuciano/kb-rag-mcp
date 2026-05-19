# tests/test_legacy_parsers.py
import io
import struct
import zipfile
from pathlib import Path

import pytest


# ── .doc tests ──────────────────────────────────────────────────────────────

def test_extract_doc_returns_list_of_dicts(tmp_path):
    """extract_doc returns list[dict] with 'text' and 'page' keys."""
    from ingest.parsers.legacy_office import extract_doc

    from docx import Document
    doc = Document()
    doc.add_paragraph("Hello from legacy doc file")
    doc_path = tmp_path / "test.doc"
    doc.save(str(doc_path))

    result = extract_doc(doc_path)
    assert isinstance(result, list)
    assert len(result) > 0
    assert "text" in result[0]
    assert "page" in result[0]
    assert "Hello from legacy doc file" in result[0]["text"]


def test_extract_doc_missing_file_returns_empty(tmp_path):
    from ingest.parsers.legacy_office import extract_doc
    result = extract_doc(tmp_path / "nonexistent.doc")
    assert result == []


# ── .xls tests ──────────────────────────────────────────────────────────────

def test_extract_xls_missing_file_returns_empty(tmp_path):
    from ingest.parsers.legacy_office import extract_xls
    result = extract_xls(tmp_path / "nonexistent.xls")
    assert result == []


# ── .odt tests ──────────────────────────────────────────────────────────────

def test_extract_odt_returns_list_of_dicts(tmp_path):
    """extract_odt returns list[dict] for OpenDocument text files."""
    pytest.importorskip("odf", reason="odfpy required")
    from ingest.parsers.legacy_office import extract_odt

    from odf.opendocument import OpenDocumentText
    from odf.text import P

    doc = OpenDocumentText()
    p = P(text="Hello from ODT file")
    doc.text.addElement(p)
    odt_path = tmp_path / "test.odt"
    doc.save(str(odt_path))

    result = extract_odt(odt_path)
    assert isinstance(result, list)
    assert len(result) > 0
    assert "Hello from ODT file" in result[0]["text"]


def test_extract_odt_missing_file_returns_empty(tmp_path):
    pytest.importorskip("odf", reason="odfpy required")
    from ingest.parsers.legacy_office import extract_odt
    result = extract_odt(tmp_path / "nonexistent.odt")
    assert result == []


# ── integration tests ────────────────────────────────────────────────────────

def test_ingest_ext_type_map_includes_legacy():
    """EXT_TYPE_MAP in ingest.py includes all new legacy extensions."""
    from ingest.ingest import EXT_TYPE_MAP
    for ext in [".doc", ".xls", ".ppt", ".odt", ".ods", ".odp", ".wpd", ".zip"]:
        assert ext in EXT_TYPE_MAP, f"{ext} not in EXT_TYPE_MAP"


def test_ingest_extractors_includes_legacy():
    """EXTRACTORS dict has entries for all legacy file types."""
    from ingest.ingest import EXTRACTORS
    for key in ["doc", "xls", "ppt", "odt", "ods", "odp", "wpd", "zip"]:
        assert key in EXTRACTORS, f"'{key}' not in EXTRACTORS"
