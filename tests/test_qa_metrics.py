import pytest
from qa.metrics import hit_rate

def test_hit_rate_basic():
    # Each sublist contains the retrieved chunk IDs for one query
    retrieved_results = [["id1", "id2", "id3"], ["id3", "id4"], ["id5"]]
    golden_answers = ["id2", "id4", "id5"]
    result = hit_rate(retrieved_results, golden_answers)
    assert result == 1.0

def test_hit_rate_partial():
    retrieved_results = [["a", "b"], ["c"], ["d", "e"]]
    golden_answers = ["b", "z", "e"]  # Only 2 hits
    result = hit_rate(retrieved_results, golden_answers)
    assert result == pytest.approx(2/3)

def test_hit_rate_none():
    retrieved_results = [["id1"], ["id2"], ["id3"]]
    golden_answers = ["x", "y", "z"]  # No hits
    result = hit_rate(retrieved_results, golden_answers)
    assert result == 0.0

def test_hit_rate_empty():
    assert hit_rate([], []) == 0.0
