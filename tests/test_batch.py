"""
FASE 8: Tests for batch processing optimizations.

Tests connection pooling, batch embedding, and batch upsert operations.
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest


@pytest.fixture
def mock_http_client():
    """Mock httpx.AsyncClient."""
    client = AsyncMock()
    client.post = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_qdrant_client():
    """Mock AsyncQdrantClient."""
    client = AsyncMock()
    client.upsert = AsyncMock()
    client.close = AsyncMock()
    client.get_collections = AsyncMock()
    client.get_collections.return_value = Mock(collections=[])
    client.create_collection = AsyncMock()
    return client


# ─────────────────────────────────────────────────────────────────────
# Connection Pooling Tests
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_http_client_connection_pooling():
    """Test HTTP client is created with connection pooling."""
    with patch("kb_server.embed_client.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_client_cls.return_value = mock_instance
        
        from kb_server import embed_client
        
        # Reset global client
        embed_client._http_client = None
        
        # Get client
        client = await embed_client._http()
        
        # Verify client created with pooling config
        mock_client_cls.assert_called_once()
        call_kwargs = mock_client_cls.call_args.kwargs
        
        assert "limits" in call_kwargs
        assert "timeout" in call_kwargs
        assert call_kwargs.get("http2") is True
        
        # Verify same client reused
        client2 = await embed_client._http()
        assert client2 is mock_instance


@pytest.mark.asyncio
async def test_http_client_close():
    """Test HTTP client cleanup."""
    with patch("kb_server.embed_client.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_client_cls.return_value = mock_instance
        
        from kb_server import embed_client
        
        # Reset and create client
        embed_client._http_client = None
        await embed_client._http()
        
        # Close
        await embed_client.close()
        
        # Verify cleanup
        mock_instance.aclose.assert_called_once()
        assert embed_client._http_client is None


@pytest.mark.asyncio
async def test_qdrant_connection_pooling_http():
    """Test Qdrant client HTTP connection."""
    with (
        patch("kb_server.vector_store.AsyncQdrantClient") as mock_client_cls,
        patch.dict("os.environ", {"QDRANT_GRPC": "false"}),
    ):
        mock_instance = AsyncMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.get_collections = AsyncMock(
            return_value=Mock(collections=[])
        )
        mock_instance.create_collection = AsyncMock()
        
        from kb_server.vector_store import VectorStore
        
        store = VectorStore()
        await store.connect()
        
        # Verify HTTP connection
        mock_client_cls.assert_called_once()
        call_kwargs = mock_client_cls.call_args.kwargs
        
        assert "host" in call_kwargs
        assert "port" in call_kwargs
        assert "timeout" in call_kwargs
        assert "prefer_grpc" not in call_kwargs


@pytest.mark.asyncio
async def test_qdrant_connection_pooling_grpc():
    """Test Qdrant client gRPC connection."""
    with (
        patch("kb_server.vector_store.AsyncQdrantClient") as mock_client_cls,
        patch("kb_server.vector_store.QDRANT_GRPC", True),
        patch("kb_server.vector_store.QDRANT_GRPC_PORT", 6334),
    ):
        mock_instance = AsyncMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.get_collections = AsyncMock(
            return_value=Mock(collections=[])
        )
        mock_instance.create_collection = AsyncMock()

        from kb_server.vector_store import VectorStore

        store = VectorStore()
        await store.connect()

        # Verify gRPC connection
        call_kwargs = mock_client_cls.call_args.kwargs

        assert call_kwargs.get("prefer_grpc") is True
        assert call_kwargs.get("grpc_port") == 6334


# ─────────────────────────────────────────────────────────────────────
# Batch Embedding Tests
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_batch_embedding_openai_compat_native_api():
    """Test batch embedding uses native OpenAI-compatible batch API."""
    with (
        patch("kb_server.embed_client._http") as mock_http,
        patch.dict("os.environ", {"EMBED_BACKEND": "openai-compat"}),
    ):
        mock_client = AsyncMock()
        mock_http.return_value = mock_client
        
        # Mock response with batch data
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"index": 0, "embedding": [0.1] * 768},
                {"index": 1, "embedding": [0.2] * 768},
                {"index": 2, "embedding": [0.3] * 768},
            ]
        }
        mock_client.post.return_value = mock_response
        
        from kb_server.embed_client import get_embeddings_batch
        
        texts = ["text 1", "text 2", "text 3"]
        vectors = await get_embeddings_batch(
            texts, batch_size=10, use_cache=False
        )
        
        # Verify single API call (not 3 separate calls)
        assert mock_client.post.call_count == 1
        
        # Verify correct payload
        call_kwargs = mock_client.post.call_args.kwargs
        payload = call_kwargs["json"]
        assert payload["input"] == texts  # All texts in one call
        
        # Verify results
        assert len(vectors) == 3
        assert vectors[0][0] == 0.1
        assert vectors[1][0] == 0.2
        assert vectors[2][0] == 0.3


@pytest.mark.asyncio
async def test_batch_embedding_cache_integration():
    """Test batch embedding uses cache efficiently."""
    with (
        patch("kb_server.embed_client._http") as mock_http,
        patch.dict("os.environ", {"EMBED_BACKEND": "openai-compat"}),
    ):
        mock_client = AsyncMock()
        mock_http.return_value = mock_client
        
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"index": i, "embedding": [float(i)] * 768}
                     for i in range(5)]
        }
        mock_client.post.return_value = mock_response
        
        from kb_server.embed_client import (
            get_embeddings_batch,
            init_cache,
        )
        from kb_server.cache.manager import CacheManager
        
        # Initialize cache
        cache = CacheManager(backend="lru", max_size_mb=10)
        init_cache(cache)
        
        texts = [f"text {i}" for i in range(5)]
        
        # First call - cache miss
        vectors1 = await get_embeddings_batch(texts, batch_size=10)
        api_calls_first = mock_client.post.call_count
        
        # Second call - cache hit
        vectors2 = await get_embeddings_batch(texts, batch_size=10)
        api_calls_second = mock_client.post.call_count
        
        # Verify cache working
        assert api_calls_second == api_calls_first  # No new API calls
        assert vectors1 == vectors2


@pytest.mark.asyncio
async def test_batch_embedding_handles_large_batches():
    """Test batch embedding splits large inputs into sub-batches."""
    with (
        patch("kb_server.embed_client._http") as mock_http,
        patch.dict("os.environ", {"EMBED_BACKEND": "openai-compat"}),
    ):
        mock_client = AsyncMock()
        mock_http.return_value = mock_client
        
        # Mock response
        mock_response = Mock()
        
        def create_response(*args, **kwargs):
            payload = kwargs["json"]
            input_texts = payload["input"]
            return Mock(
                json=lambda: {
                    "data": [
                        {"index": i, "embedding": [0.1] * 768}
                        for i in range(len(input_texts))
                    ]
                }
            )
        
        mock_client.post.side_effect = create_response
        
        from kb_server.embed_client import get_embeddings_batch
        
        # 100 texts with batch_size=32
        texts = [f"text {i}" for i in range(100)]
        vectors = await get_embeddings_batch(
            texts, batch_size=32, use_cache=False
        )
        
        # Verify multiple API calls (100 / 32 = 4 batches)
        assert mock_client.post.call_count == 4
        
        # Verify all vectors returned
        assert len(vectors) == 100


@pytest.mark.asyncio
async def test_batch_embedding_preserves_order():
    """Test batch embedding returns vectors in correct order."""
    with (
        patch("kb_server.embed_client._http") as mock_http,
        patch.dict("os.environ", {"EMBED_BACKEND": "openai-compat"}),
    ):
        mock_client = AsyncMock()
        mock_http.return_value = mock_client
        
        # Mock response with shuffled indices (simulating out-of-order)
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"index": 2, "embedding": [0.3] * 768},
                {"index": 0, "embedding": [0.1] * 768},
                {"index": 1, "embedding": [0.2] * 768},
            ]
        }
        mock_client.post.return_value = mock_response
        
        from kb_server.embed_client import get_embeddings_batch
        
        texts = ["first", "second", "third"]
        vectors = await get_embeddings_batch(
            texts, batch_size=10, use_cache=False
        )
        
        # Verify correct order (sorted by index)
        assert vectors[0][0] == 0.1  # first
        assert vectors[1][0] == 0.2  # second
        assert vectors[2][0] == 0.3  # third


# ─────────────────────────────────────────────────────────────────────
# Batch Upsert Tests
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_qdrant_batch_upsert_basic():
    """Test basic batch upsert operation."""
    with patch("kb_server.vector_store.AsyncQdrantClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_collections = AsyncMock(
            return_value=Mock(
                collections=[Mock(name="kb_docs")]
            )
        )
        
        from kb_server.vector_store import VectorStore
        
        store = VectorStore()
        store.client = mock_client
        
        # Prepare chunks
        chunks = [
            {
                "text": f"chunk {i}",
                "vector": [0.1] * 768,
                "source_file": "test.pdf",
                "file_type": "pdf",
                "product": "test",
                "chunk_index": i,
            }
            for i in range(50)
        ]
        
        await store.upsert_chunks(chunks)
        
        # Verify upsert called
        assert mock_client.upsert.call_count >= 1
        
        # Verify all points uploaded
        total_points = sum(
            len(call.kwargs["points"])
            for call in mock_client.upsert.call_args_list
        )
        assert total_points == 50


@pytest.mark.asyncio
async def test_qdrant_batch_upsert_splits_large_batches():
    """Test batch upsert splits large inputs correctly."""
    with (
        patch("kb_server.vector_store.AsyncQdrantClient") as mock_client_cls,
        patch.dict("os.environ", {"QDRANT_BATCH_SIZE": "50"}),
    ):
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_collections = AsyncMock(
            return_value=Mock(
                collections=[Mock(name="kb_docs")]
            )
        )
        
        from kb_server.vector_store import VectorStore
        
        store = VectorStore()
        store.client = mock_client
        store.batch_size = 50
        
        # 200 chunks = 4 batches
        chunks = [
            {
                "text": f"chunk {i}",
                "vector": [0.1] * 768,
                "source_file": "test.pdf",
                "file_type": "pdf",
                "product": "test",
                "chunk_index": i,
            }
            for i in range(200)
        ]
        
        await store.upsert_chunks(chunks)
        
        # Verify 4 upsert calls
        assert mock_client.upsert.call_count == 4
        
        # Verify batch sizes
        for call in mock_client.upsert.call_args_list:
            points = call.kwargs["points"]
            assert len(points) <= 50


@pytest.mark.asyncio
async def test_qdrant_parallel_batch_upsert():
    """Test parallel batch upsert for large datasets."""
    with patch("kb_server.vector_store.AsyncQdrantClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_collections = AsyncMock(
            return_value=Mock(
                collections=[Mock(name="kb_docs")]
            )
        )
        
        # Track timing
        call_times = []
        
        async def mock_upsert(*args, **kwargs):
            call_times.append(time.time())
            await asyncio.sleep(0.1)  # Simulate network delay
        
        mock_client.upsert = mock_upsert
        
        from kb_server.vector_store import VectorStore
        
        store = VectorStore()
        store.client = mock_client
        store.batch_size = 100
        
        # 300 chunks = 3 batches
        chunks = [
            {
                "text": f"chunk {i}",
                "vector": [0.1] * 768,
                "source_file": "test.pdf",
                "file_type": "pdf",
                "product": "test",
                "chunk_index": i,
            }
            for i in range(300)
        ]
        
        start = time.time()
        await store.upsert_chunks_parallel(chunks, max_parallel=3)
        elapsed = time.time() - start
        
        # Verify parallel execution (should be ~0.1s not ~0.3s)
        assert elapsed < 0.25  # Allow some overhead
        
        # Verify all batches processed
        assert len(call_times) == 3


# ─────────────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_batch_processor_end_to_end(tmp_path):
    """Test BatchDocumentProcessor end-to-end flow."""
    from ingest.worker.batch_processor import (
        BatchDocumentProcessor,
        FileChunk,
    )
    
    # Create test files
    test_file = tmp_path / "test.txt"
    test_file.write_text("This is test content.")
    
    # Mock components
    mock_store = AsyncMock()
    mock_store.upsert_chunks = AsyncMock()
    mock_registry = Mock()
    mock_registry.is_indexed = Mock(return_value=False)
    mock_registry.mark_indexed = Mock()
    
    with (
        patch("kb_server.embed_client.get_embeddings_batch") as mock_embed,
        patch("ingest.ingest.parse_document") as mock_parse,
        patch("ingest.classifier.classify_document") as mock_classify,
    ):
        # Mock parse
        mock_parse.return_value = [
            {
                "text": "chunk 1",
                "file_type": "txt",
                "page": None,
            },
            {
                "text": "chunk 2",
                "file_type": "txt",
                "page": None,
            },
        ]
        
        # Mock classify
        mock_classify.return_value = {
            "product": "test",
            "doc_type": "document",
        }
        
        # Mock embed
        mock_embed.return_value = [
            [0.1] * 768,
            [0.2] * 768,
        ]
        
        processor = BatchDocumentProcessor(
            vector_store=mock_store,
            registry=mock_registry,
            batch_size=10,
            skip_validation=True,
        )
        
        result = await processor.process_files(
            [test_file],
            docs_root=tmp_path,
            force=False,
        )
        
        # Verify success
        assert result.success_files == 1
        assert result.total_chunks == 2
        assert len(result.failed_files) == 0
        
        # Verify embed called with batch
        mock_embed.assert_called_once()
        embed_args = mock_embed.call_args[0][0]
        assert len(embed_args) == 2
        
        # Verify upsert called
        mock_store.upsert_chunks.assert_called_once()
        upsert_args = mock_store.upsert_chunks.call_args[0][0]
        assert len(upsert_args) == 2


@pytest.mark.asyncio
async def test_batch_config_auto_tuning():
    """Test batch configuration auto-tuning."""
    from config.batch_config import get_optimal_batch_sizes
    
    sizes = get_optimal_batch_sizes()
    
    # Verify all keys present
    assert "embed_batch_size" in sizes
    assert "file_batch_size" in sizes
    assert "qdrant_batch_size" in sizes
    assert "http_pool_size" in sizes
    assert "num_workers" in sizes
    
    # Verify reasonable values
    assert sizes["embed_batch_size"] > 0
    assert sizes["file_batch_size"] > 0
    assert sizes["num_workers"] >= 1


def test_batch_config_env_override():
    """Test batch config respects environment variables."""
    with patch.dict(
        "os.environ",
        {
            "EMBED_BATCH_SIZE": "128",
            "FILE_BATCH_SIZE": "200",
            "NUM_WORKERS": "16",
        },
    ):
        # Force reload of config module
        import importlib
        import config.batch_config
        
        importlib.reload(config.batch_config)
        
        assert config.batch_config.EMBED_BATCH_SIZE == 128
        assert config.batch_config.FILE_BATCH_SIZE == 200
        assert config.batch_config.NUM_WORKERS == 16
