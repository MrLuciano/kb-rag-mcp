"""
QA Embedder — thin async wrapper around the production embedding backend.

Uses the same kb_server.embed_client as the ingest pipeline, ensuring
vectors are always compatible with what is stored in Qdrant.
"""
import asyncio
import kb_server  # noqa: F401 - must be imported before mcp pollutes sys.modules

from kb_server.embed_client import get_embedding, get_embeddings_batch, get_embed_dim


class Embedder:
    def __init__(self, model_name: str = ""):
        # model_name is accepted for API compatibility but ignored;
        # the actual model is controlled by EMBED_MODEL env var.
        self.dim = get_embed_dim()

    def embed(self, text: str) -> list[float]:
        """Synchronous embed — runs the async call in a new event loop."""
        return asyncio.run(get_embedding(text))

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Synchronous batch embed — runs the async call in a new event loop."""
        return asyncio.run(get_embeddings_batch(texts))

    async def aembed(self, text: str) -> list[float]:
        """Async single embed."""
        return await get_embedding(text)

    async def aembed_batch(self, texts: list[str]) -> list[list[float]]:
        """Async batch embed."""
        return await get_embeddings_batch(texts)
