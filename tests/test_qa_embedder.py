import pytest
from unittest.mock import AsyncMock, patch

FAKE_DIM = 768
FAKE_VEC = [0.1] * FAKE_DIM


@pytest.mark.asyncio
async def test_embedder_single():
    with patch(
        "qa.embedder.get_embedding", new=AsyncMock(return_value=FAKE_VEC)
    ):
        from qa.embedder import Embedder

        embedder = Embedder()
        vec = await embedder.aembed("hello world")
    assert isinstance(vec, list)
    assert len(vec) == FAKE_DIM


@pytest.mark.asyncio
async def test_embedder_batch():
    with patch(
        "qa.embedder.get_embeddings_batch",
        new=AsyncMock(return_value=[FAKE_VEC, FAKE_VEC]),
    ):
        from qa.embedder import Embedder

        embedder = Embedder()
        out = await embedder.aembed_batch(["abc", "def"])
    assert isinstance(out, list)
    assert len(out) == 2
    assert all(len(v) == FAKE_DIM for v in out)


def test_embedder_dim():
    """Embedder.dim matches get_embed_dim() from production embed_client."""
    with patch("qa.embedder.get_embed_dim", return_value=FAKE_DIM):
        from importlib import reload
        import qa.embedder as emb_module

        reload(emb_module)
        embedder = emb_module.Embedder()
    assert embedder.dim == FAKE_DIM
