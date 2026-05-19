# Testing Patterns

**Analysis Date:** 2026-05-19

## Test Framework

**Runner:**
- pytest
- Config: `pyproject.toml` (`[tool.pytest.ini_options]`)
- `asyncio_mode = "strict"` — all async tests require explicit `@pytest.mark.asyncio`
- `pythonpath = ["."]` — project root on path

**Assertion Library:**
- pytest built-in assertions (no third-party)

**Async Support:**
- `pytest-asyncio` with strict mode

**Run Commands:**
```bash
pytest tests/                    # Run all tests
pytest tests/ -k "test_health"   # Run specific tests
pytest tests/ -m fase12          # Run by marker
pytest tests/e2e/                # E2E tests only
pytest tests/ --co -q            # Collect/list tests
```

## Test File Organization

**Location:**
- All unit/integration tests in `tests/` at project root (separate from source)
- E2E tests in `tests/e2e/` subdirectory
- Source mirrors NOT used — tests named by subject area

**Naming:**
- `test_<subject>.py`: `test_hybrid_search.py`, `test_validation.py`, `test_worker_system.py`
- E2E: `test_<workflow>_workflow.py`: `test_health_workflow.py`, `test_ingestion_workflow.py`

**Structure:**
```
tests/
├── conftest.py              # Session fixture: loads .env
├── e2e/
│   ├── conftest.py          # E2E-specific fixtures
│   ├── test_deployment_workflow.py
│   ├── test_health_workflow.py
│   └── test_ingestion_workflow.py
├── test_batch.py
├── test_cli.py
├── test_collection_manager.py
├── test_health.py
├── test_hybrid_search.py
├── test_validation.py
├── test_worker_system.py
└── ... (39 total test files, 339 test functions)
```

## Test Structure

**Suite Organization — flat functions:**
```python
"""Tests for health check system."""
import pytest
from fastapi.testclient import TestClient

def test_health_basic():
    """Test basic health endpoint returns 200."""
    from kb_server.health_server import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

**Suite Organization — class-based:**
```python
class TestHybridSearcher:
    @pytest.fixture
    def hybrid_searcher(self):
        from kb_server.retrieval.hybrid_search import HybridSearcher
        return HybridSearcher()

    @pytest.mark.asyncio
    async def test_rrf_fusion_combines_results(self, hybrid_searcher):
        ...
```

**Both styles are used.** Class grouping is used for related tests sharing fixtures. Top-level functions for independent checks.

**Patterns:**
- Imports inside test functions: `from kb_server.health_server import app` — avoids circular imports at collection time
- Every test function has a docstring describing what it verifies
- Descriptive test names: `test_rate_limiter_enforces_rate`, `test_rrf_fusion_empty_sparse`

## Fixtures

**conftest.py (session-scoped):**
```python
@pytest.fixture(scope='session', autouse=True)
def load_dotenv_once():
    """Loads .env from project root before any tests execute."""
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
```

**Local fixtures with `tmp_path`:**
```python
@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for test files."""
    return tmp_path

@pytest.fixture
def sample_text_file(temp_dir):
    """Create a sample text file."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("Hello, world!", encoding="utf-8")
    return file_path
```

**Class-scoped fixtures:**
```python
class TestHybridSearcher:
    @pytest.fixture
    def hybrid_searcher(self):
        from kb_server.retrieval.hybrid_search import HybridSearcher
        return HybridSearcher()
```

## Mocking

**Framework:** `unittest.mock` (stdlib)

**Imports:**
```python
from unittest.mock import AsyncMock, MagicMock, patch
```

**Patterns:**
```python
# Patch as context manager
with patch("module.ClassName") as mock_cls:
    mock_cls.return_value = MagicMock()

# Async mocking
mock_fn = AsyncMock(return_value={"status": "ok"})

# @patch decorator
@patch("kb_server.vector_store.QdrantClient")
def test_something(mock_client):
    mock_client.return_value.search.return_value = []
```

**104 mock usages** across test files (grep count).

**What to Mock:**
- External services: QdrantClient, embedding models, LLM API calls
- File I/O for edge cases (use `tmp_path` for real files)
- Network calls and slow operations

**What NOT to Mock:**
- Pure Python logic (validators, rate limiters, data classes)
- Internal business logic under test

## Error Testing

**Pattern:**
```python
with pytest.raises(CollectionNotFoundError, match="custom"):
    await router.route_query("custom", query)

with pytest.raises(ValueError, match="Invalid doc_type"):
    meta_loader.load("bad_type")

with pytest.raises(NotImplementedError):
    abstract_base.unimplemented_method()
```

- Always use `match=` parameter to verify error message content
- `pytest.raises` used as context manager exclusively

## Async Testing

**Pattern:**
```python
@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """Test basic rate limiter functionality."""
    limiter = RateLimiter(requests_per_minute=60.0)
    start = asyncio.get_event_loop().time()
    await limiter.acquire()
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed < 0.1
```

- `asyncio_mode = "strict"` means `@pytest.mark.asyncio` is required on every async test
- Top-level and class-method async tests both work

## Test Markers

**Custom markers used:**
- `@pytest.mark.asyncio` — async tests
- `pytest.mark.fase12` — tests for FASE 12 features (set via `pytestmark`)
- `@pytest.mark.integration` — integration tests requiring external services
- `@pytest.mark.cli` — CLI-focused tests
- `@pytest.mark.skip(reason="...")` — expensive tests (e.g., LLM API calls)
- `@pytest.mark.skipif(...)` — conditional skips in E2E tests

**Module-level marker assignment:**
```python
pytestmark = pytest.mark.fase12
```

## E2E Tests

**Location:** `tests/e2e/`

**Pattern:** Workflow-oriented, test full user journeys. Use `@pytest.mark.skipif` for environment-dependent tests.

**Runner:** `tests/e2e/run_e2e_tests.py` — dedicated script for E2E execution.

## Coverage

**Requirements:** Not enforced (no `--cov` in pyproject.toml)

**Run with coverage:**
```bash
pytest tests/ --cov=kb_server --cov=ingest --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- Pure logic: validators, rate limiters, data transformations
- No external dependencies
- Files: `test_validation.py`, `test_worker_system.py`, `test_hybrid_rrf.py`

**Integration Tests:**
- Test FastAPI endpoints via `TestClient`
- Test component interactions
- Marked `@pytest.mark.integration`
- Files: `test_health.py`, `test_collection_router.py`, `test_query_logging_integration.py`

**E2E Tests:**
- Full workflow tests against running services
- Located in `tests/e2e/`
- Files: `test_health_workflow.py`, `test_ingestion_workflow.py`, `test_deployment_workflow.py`

---

*Testing analysis: 2026-05-19*
