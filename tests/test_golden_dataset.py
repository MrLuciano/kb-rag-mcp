"""Tests for kb_server/evaluation/dataset.py and csv_loader.py."""
import json
from pathlib import Path

import pytest

from kb_server.evaluation.csv_loader import CSVDatasetLoader
from kb_server.evaluation.dataset import GoldenDataset


# ── CSVDatasetLoader tests ──────────────────────────────────────────────


class TestCSVDatasetLoader:
    def test_comma_delimiter(self, tmp_path: Path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(
            "query,expected_answer,expected_docs,metadata\n"
            "How to install?,Run installer,doc1.pdf,{}\n"
            "How to config?,Edit config,doc2.pdf;doc3.pdf,{\"product\":\"X\"}\n"
        )
        result = CSVDatasetLoader.load(csv_path)
        assert len(result) == 2
        assert result[0]["query"] == "How to install?"
        assert result[0]["expected_answer"] == "Run installer"
        assert result[0]["expected_docs"] == ["doc1.pdf"]
        assert result[0]["metadata"] == {}

    def test_semicolon_delimiter(self, tmp_path: Path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(
            "query;expected_answer;expected_docs;metadata\n"
            "How to install?;Run installer;doc1.pdf;{}\n"
        )
        result = CSVDatasetLoader.load(csv_path)
        assert len(result) == 1
        assert result[0]["query"] == "How to install?"

    def test_tab_delimiter(self, tmp_path: Path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(
            "query\texpected_answer\texpected_docs\tmetadata\n"
            "How to install?\tRun installer\tdoc1.pdf\t{}\n"
        )
        result = CSVDatasetLoader.load(csv_path)
        assert len(result) == 1
        assert result[0]["query"] == "How to install?"

    def test_missing_required_columns(self, tmp_path: Path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("query,expected_docs\n" "How to install?,doc1.pdf\n")
        with pytest.raises(ValueError) as exc_info:
            CSVDatasetLoader.load(csv_path)
        assert "expected_answer" in str(exc_info.value)

    def test_empty_file(self, tmp_path: Path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("")
        with pytest.raises(ValueError) as exc_info:
            CSVDatasetLoader.load(csv_path)
        assert "empty" in str(exc_info.value)

    def test_expected_docs_parsing(self, tmp_path: Path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(
            'query,expected_answer,expected_docs\n'
            '"Q1","A1","doc1.pdf, doc2.pdf"\n'
            '"Q2","A2",""\n'
            '"Q3","A3"," single_doc.pdf "\n'
        )
        result = CSVDatasetLoader.load(csv_path)
        assert result[0]["expected_docs"] == ["doc1.pdf", "doc2.pdf"]
        assert result[1]["expected_docs"] == []
        assert result[2]["expected_docs"] == ["single_doc.pdf"]

    def test_metadata_json_parsing(self, tmp_path: Path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(
            "query,expected_answer,metadata\n"
            'Q1,A1,"{""product"": ""X"", ""version"": ""1.0""}"\n'
        )
        result = CSVDatasetLoader.load(csv_path)
        assert result[0]["metadata"] == {"product": "X", "version": "1.0"}

    def test_metadata_invalid_json_fallback(self, tmp_path: Path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(
            "query,expected_answer,metadata\n"
            "Q1,A1,not-json\n"
        )
        result = CSVDatasetLoader.load(csv_path)
        assert result[0]["metadata"] == {"raw": "not-json"}


# ── GoldenDataset tests ──────────────────────────────────────────────────


class TestGoldenDatasetJSON:
    def test_load_json(self, tmp_path: Path):
        json_path = tmp_path / "dataset.json"
        json_path.write_text(json.dumps([
            {
                "query": "How to install?",
                "expected_answer": "Run installer.",
                "expected_docs": ["doc1.pdf"],
            }
        ]))
        dataset = GoldenDataset(json_path)
        assert len(dataset) == 1
        assert dataset[0]["query"] == "How to install?"

    def test_load_missing_file_returns_empty(self, tmp_path: Path):
        json_path = tmp_path / "nonexistent.json"
        dataset = GoldenDataset(json_path)
        assert len(dataset) == 0

    def test_add_example(self, tmp_path: Path):
        json_path = tmp_path / "dataset.json"
        json_path.write_text("[]")
        dataset = GoldenDataset(json_path)
        dataset.add_example("Q", "A", ["doc.pdf"], {"product": "X"})
        assert len(dataset) == 1
        assert dataset[0]["metadata"]["product"] == "X"

    def test_save(self, tmp_path: Path):
        json_path = tmp_path / "dataset.json"
        json_path.write_text("[]")
        dataset = GoldenDataset(json_path)
        dataset.add_example("Q", "A", ["doc.pdf"])
        dataset.save()
        data = json.loads(json_path.read_text())
        assert len(data) == 1

    def test_validate_catches_empty_fields(self, tmp_path: Path):
        json_path = tmp_path / "dataset.json"
        json_path.write_text(json.dumps([
            {"query": "", "expected_answer": "", "expected_docs": []},
            {"query": "OK", "expected_answer": "OK", "expected_docs": ["doc"]},
        ]))
        dataset = GoldenDataset(json_path)
        errors = dataset.validate()
        assert len(errors) == 3  # empty query, empty answer, empty docs

    def test_validate_catches_wrong_type(self, tmp_path: Path):
        json_path = tmp_path / "dataset.json"
        json_path.write_text(json.dumps([
            {"query": "Q", "expected_answer": "A", "expected_docs": "not-a-list"},
        ]))
        dataset = GoldenDataset(json_path)
        errors = dataset.validate()
        assert any("must be a list" in e for e in errors)


class TestGoldenDatasetCSV:
    def test_load_csv(self, tmp_path: Path):
        csv_path = tmp_path / "dataset.csv"
        csv_path.write_text(
            "query,expected_answer,expected_docs\n"
            "How to install?,Run installer,doc1.pdf\n"
        )
        dataset = GoldenDataset(csv_path)
        assert len(dataset) == 1
        assert dataset[0]["query"] == "How to install?"

    def test_from_csv_classmethod(self, tmp_path: Path):
        csv_path = tmp_path / "dataset.csv"
        csv_path.write_text(
            "query,expected_answer\n"
            "Q1,A1\n"
        )
        dataset = GoldenDataset.from_csv(csv_path)
        assert len(dataset) == 1

    def test_unsupported_extension_raises(self, tmp_path: Path):
        txt_path = tmp_path / "dataset.txt"
        txt_path.write_text("test")
        with pytest.raises(ValueError) as exc_info:
            GoldenDataset(txt_path)
        assert ".txt" in str(exc_info.value)

    def test_csv_and_json_equivalent(self, tmp_path: Path):
        # Create equivalent JSON and CSV datasets
        json_path = tmp_path / "data.json"
        json_path.write_text(json.dumps([
            {"query": "Q1", "expected_answer": "A1", "expected_docs": ["d1"], "metadata": {}},
        ]))

        csv_path = tmp_path / "data.csv"
        csv_path.write_text(
            "query,expected_answer,expected_docs,metadata\n"
            "Q1,A1,d1,{}\n"
        )

        json_ds = GoldenDataset(json_path)
        csv_ds = GoldenDataset(csv_path)

        assert len(json_ds) == len(csv_ds)
        assert json_ds[0]["query"] == csv_ds[0]["query"]
        assert json_ds[0]["expected_answer"] == csv_ds[0]["expected_answer"]
