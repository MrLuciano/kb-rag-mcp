# Coding Conventions

**Analysis Date:** 2026-05-19

## Naming Patterns

**Files:**
- `snake_case` for all Python modules: `hybrid_search.py`, `batch_processor.py`, `query_analyzer.py`
- Package names in `snake_case` directories: `kb_server/`, `ingest/`, `kb_server/retrieval/`
- Test files prefixed with `test_`: `test_hybrid_search.py`, `test_validation.py`

**Classes:**
- `PascalCase`: `HybridSearcher`, `FileWorker`, `ValidationPipeline`, `CollectionManager`
- Exceptions suffixed with `Error`: `CollectionNotFoundError`, `ValidationError`
- Abstract base classes use ABC: `class Validator(ABC):`

**Functions/Methods:**
- `snake_case` for all functions and methods: `_rrf_fusion()`, `_load_sparse_model()`, `check_all_components()`
- Private/internal methods prefixed with `_`: `_rrf_fusion`, `_load_sparse_model`
- Factory functions prefixed with `create_`: `create_default_pipeline()`, `create_strict_pipeline()`, `create_lenient_pipeline()`

**Variables:**
- `snake_case` for local variables and module-level config
- `UPPER_SNAKE_CASE` for module-level constants read from env: `TOP_K`, `HYBRID_RRF_K`, `QUERY_LOG_ENABLED`
- Module logger always named `log`: `log = logging.getLogger("kb-mcp")`

**Enums:**
- `PascalCase` for enum class, `UPPER_SNAKE_CASE` for values: `ValidationSeverity.ERROR`
- Enums inherit from `str, Enum` for JSON serialization

## Code Style

**Formatting:**
- Black, line length 79 (`[tool.black]` in `pyproject.toml`)
- Target: Python 3.11+

**Imports:**
- isort with black profile, line length 79 (`[tool.isort]`)
- `from __future__ import annotations` NOT used (py3.11)

**Linting:**
- flake8, max line 79, extends-ignore E203/W503 (`.flake8`)
- mypy with `warn_return_any=true`, `ignore_missing_imports=true`

## Import Organization

**Order:**
1. Standard library (`asyncio`, `logging`, `os`, `sys`, `pathlib`)
2. Third-party packages (`fastapi`, `mcp`, `qdrant_client`)
3. Local/project imports (`from kb_server.embed_client import ...`, `from ingest.worker ...`)

**Separators:**
- Grouped with blank lines between stdlib, third-party, and local
- Seen in `server.py`: stdlib → third-party → kb_server imports

## Module Documentation

**File-level docstrings:** Every module has a triple-quoted docstring at top describing purpose. Multi-line docstrings for complex modules.

```python
"""
Hybrid Search - Combine dense vector search with BM25 sparse retrieval.

FASE 12: Search Quality Enhancement
...
"""
```

**Class docstrings:** Present on all classes with Attributes section for data classes.

**Method docstrings:** Present on public/abstract methods with Args, Returns, Raises sections.

```python
def validate(self, file_path: Path) -> ValidationResult:
    """
    Validate a document file.

    Args:
        file_path: Path to the file to validate

    Returns:
        ValidationResult indicating success or failure

    Raises:
        ValidationError: For critical validation failures
    """
```

## Type Hints

**Usage:**
- Type hints on all function signatures in production code
- `Optional[str]` for nullable params (pre-3.10 style, not `str | None`)
- New-style union syntax used in some places: `SparseTextEmbedding | None`
- `mypy` configured with `disallow_untyped_defs = false` — hints encouraged but not enforced

## Error Handling

**Patterns:**
- Try/except with explicit exception types, never bare `except:`
- Errors logged with `log.error(f"...")` before re-raise or graceful degradation
- Custom exception classes extend `Exception` and carry context objects:

```python
class ValidationError(Exception):
    def __init__(self, message: str, result: Optional[ValidationResult] = None):
        super().__init__(message)
        self.result = result
```

- Graceful degradation on optional integrations (query logger, dotenv):
```python
try:
    query_logger = QueryLogger(db_path=QUERY_LOG_PATH)
except Exception as e:
    log.error(f"Failed to initialize query logger: {e}")
    log.warning("Continuing without query logging")
```

## Logging

**Framework:** Standard `logging` module

**Logger naming convention:** Hierarchical dot notation: `"kb-mcp"`, `"kb-mcp.hybrid"`, `"kb-ingest.worker.worker"`

**Setup in entry points:**
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr), logging.FileHandler(...)]
)
log = logging.getLogger("kb-mcp")
```

**Module loggers:**
```python
log = logging.getLogger("kb-mcp.hybrid")
```

## Configuration

**Pattern:** All config loaded from `os.getenv()` with defaults at module level:

```python
HYBRID_DENSE_WEIGHT = float(os.getenv("HYBRID_DENSE_WEIGHT", "0.7"))
TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))
```

- `.env` file loaded at server startup via `python-dotenv`
- Environment variables use `UPPER_SNAKE_CASE`

## Data Classes

**Pattern:** Python `@dataclass` for simple value objects, plain classes for stateful objects:

```python
@dataclass
class ValidationResult:
    valid: bool
    severity: ValidationSeverity
    message: str
    validator_name: str
```

- Factory class methods (`@classmethod`) for common construction: `ValidationResult.success()`, `ValidationResult.failure()`

## FASE Comments

**Convention:** Development phases tagged in code and docstrings:
- Module docstrings include phase tag: `FASE 12: Search Quality Enhancement`
- Inline comments mark phase-specific features: `# FASE 14: Query logging configuration`
- Test files marked with `pytestmark = pytest.mark.fase12`

---

*Convention analysis: 2026-05-19*
