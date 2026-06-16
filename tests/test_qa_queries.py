import json
import os

import pytest


def load_queries(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def test_queries_json_loadable():
    path = os.path.join(os.path.dirname(__file__), "..", "qa", "queries.json")
    queries = load_queries(path)
    assert isinstance(queries, list)
    assert len(queries) >= 3  # Expect at least 3 queries stubbed
    for entry in queries:
        assert "question" in entry, f"Missing 'question' in {entry}"
        assert (
            "answer_chunk_id" in entry
        ), f"Missing 'answer_chunk_id' in {entry}"
        assert isinstance(entry["question"], str) and entry["question"]
        assert (
            isinstance(entry["answer_chunk_id"], str)
            and entry["answer_chunk_id"]
        )
