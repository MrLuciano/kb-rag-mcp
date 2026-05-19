"""Tests for optimization experiment stubs."""
import pytest
from kb_server.optimization.chunking_experiments import experiment_chunk_sizes
from kb_server.optimization.scoring_experiments import experiment_score_thresholds


def test_chunk_sizes_raises_not_implemented():
    """Stub: experiment_chunk_sizes raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        experiment_chunk_sizes()


def test_score_thresholds_raises_not_implemented():
    """Stub: experiment_score_thresholds raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        experiment_score_thresholds()
