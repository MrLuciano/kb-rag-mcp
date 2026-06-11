"""
Tests for graph metadata derivation (Phase 30).
"""

import pytest

from ingest.graph_builder import (
    build_graph_metadata,
    compute_document_id,
    compute_related_hints,
    extract_entities,
    extract_topics,
)


class TestDocumentId:
    def test_stable_id_from_same_input(self):
        id1 = compute_document_id("docs/guide.md", "AppServer")
        id2 = compute_document_id("docs/guide.md", "AppServer")
        assert id1 == id2
        assert len(id1) == 16

    def test_different_file_produces_different_id(self):
        id1 = compute_document_id("docs/guide.md", "AppServer")
        id2 = compute_document_id("docs/other.md", "AppServer")
        assert id1 != id2

    def test_different_product_produces_different_id(self):
        id1 = compute_document_id("docs/guide.md", "AppServer")
        id2 = compute_document_id("docs/guide.md", "DataSync")
        assert id1 != id2


class TestEntityExtraction:
    def test_extracts_top_terms(self):
        text = (
            "The database server requires configuration for replication "
            "and backup. The database cluster must use consistent settings "
            "for database replication and database backup procedures."
        )
        entities = extract_entities(text)
        assert len(entities) > 0
        assert entities[0] == "database"

    def test_empty_text_returns_empty_list(self):
        assert extract_entities("") == []

    def test_short_terms_are_filtered(self):
        text = "a an the is in on at be to of it"
        entities = extract_entities(text)
        assert all(len(e) >= 3 for e in entities)

    def test_returns_at_most_max_entities(self):
        text = (
            "apple banana cherry date elderberry fig grape "
            "honeydew kiwi lemon mango nectarine orange "
            "papaya quince raspberry strawberry tangerine"
        )
        entities = extract_entities(text)
        assert len(entities) <= 8


class TestTopicExtraction:
    def test_topics_from_product_and_doc_type(self):
        meta = {
            "product": "AppServer",
            "doc_type": "install_guide",
            "vendor": "OpenText",
        }
        topics = extract_topics(meta)
        assert "AppServer" in topics
        assert "Install Guide" in topics

    def test_module_overrides_subsystem(self):
        meta = {
            "product": "DataSync",
            "subsystem": "API",
            "module": "REST",
            "doc_type": "api_guide",
        }
        topics = extract_topics(meta)
        assert "REST" in topics
        assert "API" not in topics

    def test_vendor_included_when_different_from_product(self):
        meta = {
            "product": "OTCS",
            "vendor": "OpenText",
            "doc_type": "user_guide",
        }
        topics = extract_topics(meta)
        assert "OpenText" in topics

    def test_minimal_meta(self):
        meta = {"product": "", "doc_type": "", "vendor": ""}
        topics = extract_topics(meta)
        assert topics == []


class TestRelatedHints:
    def test_product_doc_type_hint(self):
        meta = {
            "product": "AppServer",
            "doc_type": "install_guide",
        }
        hints = compute_related_hints(meta)
        assert "product:AppServer:doc_type:install_guide" in hints

    def test_product_module_hint(self):
        meta = {
            "product": "DataSync",
            "subsystem": "API",
            "module": "REST",
        }
        hints = compute_related_hints(meta)
        assert "product:DataSync:module:REST" in hints
        assert "product:DataSync:subsystem:API" in hints

    def test_vendor_hint_when_different(self):
        meta = {
            "product": "OTCS",
            "vendor": "OpenText",
        }
        hints = compute_related_hints(meta)
        assert "vendor:OpenText" in hints

    def test_vendor_hint_omitted_when_same(self):
        meta = {
            "product": "OpenText",
            "vendor": "OpenText",
        }
        hints = compute_related_hints(meta)
        assert not any(h.startswith("vendor:") for h in hints)

    def test_empty_meta(self):
        hints = compute_related_hints({})
        assert hints == []


class TestBuildGraphMetadata:
    def test_full_pipeline(self):
        text = (
            "The AppServer installation requires Java 17 and "
            "configuration of database connections and replication settings."
        )
        meta = {
            "product": "AppServer",
            "doc_type": "install_guide",
            "vendor": "OpenText",
        }
        result = build_graph_metadata(
            text=text, source_file="docs/install.md", meta=meta
        )
        assert "doc_graph_id" in result
        assert len(result["doc_graph_id"]) == 16
        assert "graph_entities" in result
        assert len(result["graph_entities"]) > 0
        assert "graph_topics" in result
        assert "AppServer" in result["graph_topics"]
        assert "graph_related" in result
        assert len(result["graph_related"]) > 0

    def test_empty_text(self):
        meta = {"product": "Test", "doc_type": "guide"}
        result = build_graph_metadata(
            text="", source_file="empty.md", meta=meta
        )
        assert result["doc_graph_id"] == compute_document_id("empty.md", "Test")
        assert result["graph_entities"] == []
        assert "Test" in result["graph_topics"]

    def test_minimal_meta(self):
        result = build_graph_metadata(
            text="x x x", source_file="f.md", meta={}
        )
        assert result["doc_graph_id"] == compute_document_id("f.md", "")
        assert len(result["graph_entities"]) == 0
        assert result["graph_topics"] == []
        assert result["graph_related"] == []
