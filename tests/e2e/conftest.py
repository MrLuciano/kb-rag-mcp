"""
E2E test configuration and fixtures.

Provides fixtures for E2E testing including:
- Test document creation
- Temporary database setup
- Mock embedding and vector store services
- Health check utilities
"""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
import pytest
import sqlite3
import json


@pytest.fixture(scope="session")
def e2e_test_data_dir(tmp_path_factory) -> Path:
    """Create temporary directory for E2E test data."""
    return tmp_path_factory.mktemp("e2e_data")


@pytest.fixture(scope="session")
def e2e_test_docs_dir(e2e_test_data_dir: Path) -> Path:
    """Create test documents directory."""
    docs_dir = e2e_test_data_dir / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    # Create test documents
    (docs_dir / "test.txt").write_text(
        "This is a test document about Python programming."
    )
    (docs_dir / "README.md").write_text(
        "# Test Project\n\nThis is a test README file."
    )
    
    # Create product directory
    product_dir = docs_dir / "TestProduct"
    product_dir.mkdir(exist_ok=True)
    (product_dir / "manual.txt").write_text(
        "TestProduct Installation Manual\n\n"
        "Step 1: Download the software\n"
        "Step 2: Run the installer\n"
    )
    
    return docs_dir


@pytest.fixture
def e2e_temp_db(tmp_path: Path) -> Generator[Path, None, None]:
    """Create temporary SQLite database for testing."""
    db_path = tmp_path / "test_jobs.db"
    
    # Create database with schema
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            error TEXT
        )
    """)
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def e2e_temp_registry(tmp_path: Path) -> Generator[Path, None, None]:
    """Create temporary file registry database.

    Returns an empty SQLite path — IngestRegistry manages its own schema.
    """
    db_path = tmp_path / "test_registry.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    yield db_path

    if db_path.exists():
        db_path.unlink()


@pytest.fixture
async def e2e_mock_embedding_service():
    """Mock embedding service that returns fixed vectors."""
    class MockEmbeddingService:
        def __init__(self):
            self.call_count = 0
        
        async def embed_text(self, text: str) -> list[float]:
            """Return mock embedding vector."""
            self.call_count += 1
            # Return 384-dim vector (common embedding size)
            return [0.1] * 384
        
        async def embed_batch(self, texts: list[str]) -> list[list[float]]:
            """Return mock embeddings for batch."""
            self.call_count += len(texts)
            return [[0.1] * 384 for _ in texts]
    
    return MockEmbeddingService()


@pytest.fixture
def e2e_health_response() -> dict:
    """Expected health response structure."""
    return {
        "status": "ok",
        "healthy": True,
        "timestamp": pytest.approx(float, rel=1e9),  # Unix timestamp
        "components": {
            "embedding": {
                "healthy": True,
                "latency_ms": pytest.approx(float, rel=100),
            },
            "vector_store": {
                "healthy": True,
                "latency_ms": pytest.approx(float, rel=100),
            },
            "cache": {
                "healthy": True,
                "latency_ms": pytest.approx(float, rel=100),
            },
            "database": {
                "healthy": True,
                "latency_ms": pytest.approx(float, rel=100),
            },
            "filesystem": {
                "healthy": True,
                "latency_ms": pytest.approx(float, rel=100),
            },
        }
    }


@pytest.fixture
def e2e_search_params() -> dict:
    """Standard search parameters for testing."""
    return {
        "query": "Python programming",
        "top_k": 5,
        "product": None,
        "doc_type": None
    }


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
