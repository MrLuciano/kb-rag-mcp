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

# Module-level mock objects used across all tests
_mock_st = MagicMock()
_mock_cross_encoder_cls = MagicMock()
_mock_st.CrossEncoder = _mock_cross_encoder_cls


@pytest.fixture(autouse=True)
def _reset_mock():
    """Reset mock call counts and return value before each test."""
    _mock_cross_encoder_cls.reset_mock()
    _mock_cross_encoder_cls.return_value = MagicMock()


@pytest.fixture
def patched_st():
    """Ensure sentence_transformers is mocked in sys.modules during the test."""
    patcher = patch.dict(
        "sys.modules", {"sentence_transformers": _mock_st}, clear=False
    )
    patcher.start()
    yield
    patcher.stop()


def test_module_import_no_model_load(patched_st):
    """Importing kb_server.retrieval.reranker does NOT create a CrossEncoder instance.

    The module-level code in reranker.py only defines the class and the
    get_reranker() function — it never calls sentence_transformers.CrossEncoder().
    """
    # Force a fresh import by removing cached module references
    for key in list(sys.modules.keys()):
        if key.startswith("kb_server.retrieval.reranker"):
            del sys.modules[key]

    import kb_server.retrieval.reranker  # noqa: F811

    assert kb_server.retrieval.reranker.CrossEncoderReranker is not None
    _mock_cross_encoder_cls.assert_not_called()


def test_get_reranker_no_model_load(patched_st):
    """get_reranker() creates the global instance but does NOT load the model."""
    import kb_server.retrieval.reranker as reranker_mod

    # Reset the singleton so get_reranker() creates a fresh instance
    reranker_mod._reranker = None
    _mock_cross_encoder_cls.reset_mock()

    reranker = reranker_mod.get_reranker()

    # CrossEncoder must NOT have been constructed
    _mock_cross_encoder_cls.assert_not_called()
    # Model attribute must be None (not loaded yet)
    assert reranker.model is None


def test_init_no_model_load(patched_st):
    """CrossEncoderReranker.__init__() sets model=None and does not load model."""
    from kb_server.retrieval.reranker import CrossEncoderReranker

    _mock_cross_encoder_cls.reset_mock()

    reranker = CrossEncoderReranker()

    # After __init__, model must be None
    assert reranker.model is None
    # CrossEncoder must NOT have been constructed
    _mock_cross_encoder_cls.assert_not_called()


@pytest.mark.asyncio
async def test_empty_rerank_no_model_load(patched_st):
    """rerank() with empty results returns immediately without loading model."""
    from kb_server.retrieval.reranker import CrossEncoderReranker

    _mock_cross_encoder_cls.reset_mock()

    reranker = CrossEncoderReranker()
    assert reranker.model is None

    # Rerank with empty results — should return [] without calling _load_model
    result = await reranker.rerank("test query", [])

    assert result == []
    assert reranker.model is None
    # CrossEncoder must NOT have been constructed
    _mock_cross_encoder_cls.assert_not_called()
