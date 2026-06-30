"""Session-scoped mock fixtures that isolate tests from live infrastructure.

Added in Phase 6 (Test Coverage & Isolation) to satisfy TEST-02:
all unit tests run without requiring Qdrant, LM Studio, or Redis.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(scope="session", autouse=True)
def load_dotenv_once():
    """Loads .env from project root before any tests execute."""
    try:
        from dotenv import load_dotenv

        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=True)
    except ImportError:
        print(
            "[WARN] python-dotenv not installed; .env vars may be missing in tests",
            file=sys.stderr,
        )


@pytest.fixture(scope="session", autouse=True)
def mock_qdrant_client():
    """Patch AsyncQdrantClient so tests never connect to localhost:6333."""
    with patch("qdrant_client.AsyncQdrantClient") as mock:
        instance = mock.return_value
        instance.get_collections.return_value = MagicMock(collections=[])
        instance.search.return_value = []
        instance.scroll.return_value = ([], None)
        instance.count.return_value = MagicMock(count=0)
        instance.collection_exists.return_value = True
        instance.upsert.return_value = None
        instance.delete_collection.return_value = None
        instance.create_collection.return_value = None
        yield mock


@pytest.fixture(scope="function", autouse=True)
def _reset_server_module_globals():
    """Reset kb_server.server module globals after each test.

    Several test files assign mocks or None to module-level variables
    (collection_router, filter_terms_cache, query_logger) and restore
    them via per-file autouse fixtures.  If a fixture capture happens
    while the module is already contaminated (e.g. after a prior test
    file leaked a mock), the restore propagates the contamination to
    all subsequent tests.

    This conftest fixture is outermost, so its teardown runs last —
    after any per-file fixture has already restored its idea of the
    original value.  We unconditionally reset to None so the next
    test always starts with clean defaults.
    """
    yield
    import kb_server.server as srv_module

    for attr in (
        "collection_router",
        "filter_terms_cache",
        "query_logger",
    ):
        setattr(srv_module, attr, None)


@pytest.fixture(scope="session")
def mock_embed_client():
    """Patch embed client to return fixed vectors without any backend.

    NOT autouse — only applies when a test file explicitly declares this
    fixture. Embed-client-specific tests manage their own mocking.
    """
    try:
        import kb_server.embed_client as ec
    except ImportError:
        yield
        return

    fake_vector = [0.1] * 384
    with (
        patch.object(ec, "get_embedding", return_value=fake_vector),
        patch.object(ec, "get_embeddings_batch", return_value=[fake_vector]),
        patch.object(ec, "BACKEND", "test"),
        patch.object(ec, "MODEL", "test-model"),
    ):
        yield


@pytest.fixture(scope="session")
def mock_redis_cache():
    """Patch RedisCache so tests never connect to Redis.

    NOT autouse — only applies when a test file explicitly declares this
    fixture. Redis-specific tests manage their own mocking.
    """
    with patch("kb_server.cache.redis.RedisCache", autospec=True) as mock:
        yield mock
