"""
Regression tests: cross-encoder model is NOT loaded at import time.

Verifies that sentence_transformers.CrossEncoder is never constructed
at module level, during get_reranker(), or during CrossEncoderReranker.__init__().
The ~500MB model should only load on the first rerank() call that has results.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.fase12]


@pytest.fixture
def mock_objects():
    """Fixture-scoped mock objects to avoid module-level state leakage."""
    mock_st = MagicMock()
    mock_cross_encoder_cls = MagicMock()
    mock_st.CrossEncoder = mock_cross_encoder_cls
    return mock_st, mock_cross_encoder_cls


@pytest.fixture
def patched_st(mock_objects):
    """Ensure sentence_transformers is mocked in sys.modules during the test."""
    mock_st, _ = mock_objects
    patcher = patch.dict(
        "sys.modules", {"sentence_transformers": mock_st}, clear=False
    )
    patcher.start()
    yield
    patcher.stop()


@pytest.fixture(autouse=True)
def _reset_mock(mock_objects):
    """Reset mock call counts and return value before each test."""
    _, mock_cross_encoder_cls = mock_objects
    mock_cross_encoder_cls.reset_mock()
    mock_cross_encoder_cls.return_value = MagicMock()


def test_module_import_no_model_load(patched_st, mock_objects):
    """Importing kb_server.retrieval.reranker does NOT create a CrossEncoder instance.

    The module-level code in reranker.py only defines the class and the
    get_reranker() function — it never calls sentence_transformers.CrossEncoder().
    """
    _, mock_cross_encoder_cls = mock_objects
    # Force a fresh import by removing cached module references
    for key in list(sys.modules.keys()):
        if key.startswith("kb_server.retrieval.reranker"):
            del sys.modules[key]

    import kb_server.retrieval.reranker  # noqa: F811

    assert kb_server.retrieval.reranker.CrossEncoderReranker is not None
    mock_cross_encoder_cls.assert_not_called()


def test_get_reranker_no_model_load(patched_st, mock_objects):
    """get_reranker() creates the global instance but does NOT load the model."""
    _, mock_cross_encoder_cls = mock_objects
    import kb_server.retrieval.reranker as reranker_mod

    # Reset the singleton so get_reranker() creates a fresh instance
    reranker_mod._reranker = None
    mock_cross_encoder_cls.reset_mock()

    reranker = reranker_mod.get_reranker()

    # CrossEncoder must NOT have been constructed
    mock_cross_encoder_cls.assert_not_called()
    # Model attribute must be None (not loaded yet)
    assert reranker.model is None


def test_init_no_model_load(patched_st, mock_objects):
    """CrossEncoderReranker.__init__() sets model=None and does not load model."""
    _, mock_cross_encoder_cls = mock_objects
    from kb_server.retrieval.reranker import CrossEncoderReranker

    mock_cross_encoder_cls.reset_mock()

    reranker = CrossEncoderReranker()

    # After __init__, model must be None
    assert reranker.model is None
    # CrossEncoder must NOT have been constructed
    mock_cross_encoder_cls.assert_not_called()


@pytest.mark.asyncio
async def test_empty_rerank_no_model_load(patched_st, mock_objects):
    """rerank() with empty results returns immediately without loading model."""
    _, mock_cross_encoder_cls = mock_objects
    from kb_server.retrieval.reranker import CrossEncoderReranker

    mock_cross_encoder_cls.reset_mock()

    reranker = CrossEncoderReranker()
    assert reranker.model is None

    # Rerank with empty results — should return [] without calling _load_model
    result = await reranker.rerank("test query", [])

    assert result == []
    assert reranker.model is None
    # CrossEncoder must NOT have been constructed
    mock_cross_encoder_cls.assert_not_called()
