# End-to-End Test Suite

Comprehensive E2E test suite for KB-RAG-MCP covering complete workflows
from ingestion to search, health checks, and operational tasks.

## Test Structure

```
tests/e2e/
├── conftest.py                     # E2E test fixtures
├── test_ingestion_workflow.py      # Complete ingestion tests
├── test_health_workflow.py         # Health check system tests
├── test_deployment_workflow.py     # Deployment and operations tests
├── run_e2e_tests.py               # Test runner script
└── README.md                       # This file
```

## Test Categories

### 1. Ingestion Workflow Tests
**File:** `test_ingestion_workflow.py`

Tests complete document ingestion pipeline:
- Single file ingestion
- Directory ingestion with classification
- Incremental ingestion (only new/modified files)
- Error handling and recovery
- Ingestion statistics and reporting
- Product and doc_type classification

**Test Classes:**
- `TestIngestionWorkflow` - Core ingestion functionality
- `TestIngestionStats` - Statistics and reporting
- `TestRealIngestion` - Integration with real services (optional)

### 2. Health Check Workflow Tests
**File:** `test_health_workflow.py`

Tests health monitoring system:
- Individual component health checks:
  * Embedding service (LM Studio/Ollama)
  * Vector store (Qdrant)
  * Cache (LRU/Redis)
  * Database (SQLite)
  * Filesystem (disk space)
- Health aggregation and overall status
- HTTP endpoints (/health, /health/detailed, /ready, /alive)
- Latency measurements
- Health check caching

**Test Classes:**
- `TestHealthCheckComponents` - Individual checkers
- `TestHealthAggregation` - Overall health status
- `TestHealthHTTPEndpoints` - HTTP API tests
- `TestHealthCheckLatency` - Performance tests
- `TestHealthCheckCaching` - Caching behavior
- `TestRealHealthChecks` - Integration tests (optional)

### 3. Deployment Workflow Tests
**File:** `test_deployment_workflow.py`

Tests deployment and operational workflows:
- Backup creation and compression
- Restore and integrity verification
- Configuration file validation
- systemd service files
- Deployment scripts (install, backup, update)
- Directory structure
- Log rotation configuration
- Prometheus configuration and alerts

**Test Classes:**
- `TestBackupRestore` - Backup/restore operations
- `TestConfigurationValidation` - Config file checks
- `TestScriptValidation` - Deployment script checks
- `TestDirectoryStructure` - Project structure
- `TestHealthCheckIntegration` - Health system integration
- `TestLogRotation` - Log rotation config
- `TestPrometheusConfig` - Monitoring config
- `TestRealDeployment` - Real deployment tests (optional)

## Running Tests

### Run All E2E Tests

```bash
# Basic run (unit tests only, no external dependencies)
pytest tests/e2e/

# With verbose output
pytest tests/e2e/ -v

# With coverage report
pytest tests/e2e/ --cov=server --cov=ingest --cov-report=html
```

### Run Specific Test File

```bash
# Ingestion tests
pytest tests/e2e/test_ingestion_workflow.py -v

# Health tests
pytest tests/e2e/test_health_workflow.py -v

# Deployment tests
pytest tests/e2e/test_deployment_workflow.py -v
```

### Run Specific Test Class

```bash
# Test ingestion workflow
pytest tests/e2e/test_ingestion_workflow.py::TestIngestionWorkflow -v

# Test health checks
pytest tests/e2e/test_health_workflow.py::TestHealthCheckComponents -v

# Test backup/restore
pytest tests/e2e/test_deployment_workflow.py::TestBackupRestore -v
```

### Run Integration Tests

Integration tests require external services (LM Studio/Ollama, Qdrant):

```bash
# Run with integration tests
pytest tests/e2e/ --run-integration

# Or using the runner script
python tests/e2e/run_e2e_tests.py --integration -v
```

### Using Test Runner Script

```bash
# Unit tests only
python tests/e2e/run_e2e_tests.py

# With integration tests
python tests/e2e/run_e2e_tests.py --integration

# With coverage
python tests/e2e/run_e2e_tests.py --coverage -v
```

## Test Fixtures

### From `conftest.py`

**Data Fixtures:**
- `e2e_test_data_dir` - Temporary test data directory
- `e2e_test_docs_dir` - Pre-populated test documents
- `e2e_temp_db` - Temporary SQLite database
- `e2e_temp_registry` - Temporary file registry

**Mock Fixtures:**
- `e2e_mock_embedding_service` - Mock embedding API
- `e2e_health_response` - Expected health response structure
- `e2e_search_params` - Standard search parameters

**Async Fixtures:**
- `event_loop` - Event loop for async tests

## Environment Variables

Control test behavior with environment variables:

```bash
# Skip integration tests (default: enabled in unit mode)
export SKIP_INTEGRATION_TESTS=1

# Skip deployment tests (default: enabled in unit mode)
export SKIP_DEPLOYMENT_TESTS=1

# Run all tests including integration
export SKIP_INTEGRATION_TESTS=0
export SKIP_DEPLOYMENT_TESTS=0
```

## Test Coverage

Current E2E test coverage:

| Category | Tests | Coverage |
|----------|-------|----------|
| Ingestion | 8 tests | Core workflows |
| Health Checks | 15 tests | All components |
| Deployment | 12 tests | Scripts and config |
| **Total** | **35 tests** | **End-to-end** |

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run E2E tests
        run: pytest tests/e2e/ -v --cov=server --cov=ingest
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Integration Test Job

```yaml
  integration-tests:
    runs-on: ubuntu-latest
    
    services:
      qdrant:
        image: qdrant/qdrant
        ports:
          - 6333:6333
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Start LM Studio (mock)
        run: |
          # Setup mock embedding service
          python tests/mocks/embedding_server.py &
      
      - name: Run integration tests
        run: pytest tests/e2e/ --run-integration -v
```

## Test Development Guidelines

### Writing New E2E Tests

1. **Use appropriate fixtures:**
   ```python
   def test_something(e2e_test_docs_dir, e2e_temp_db):
       # Use fixtures for setup
       pass
   ```

2. **Mark integration tests:**
   ```python
   @pytest.mark.skipif(
       os.getenv("SKIP_INTEGRATION_TESTS") == "1",
       reason="Integration tests disabled"
   )
   class TestWithExternalServices:
       pass
   ```

3. **Use async for I/O:**
   ```python
   @pytest.mark.asyncio
   async def test_async_operation():
       result = await some_async_func()
       assert result is not None
   ```

4. **Clean up resources:**
   ```python
   @pytest.fixture
   def resource(tmp_path):
       # Setup
       resource = create_resource(tmp_path)
       yield resource
       # Cleanup
       resource.cleanup()
   ```

### Test Naming Convention

- `test_<feature>_<scenario>` - Basic test
- `test_<feature>_<scenario>_failure` - Error case
- `test_<feature>_integration` - Integration test
- `test_real_<feature>` - Real service test (requires external deps)

### Assertions

Be specific with assertions:

```python
# Good
assert result["status"] == "success"
assert len(results) == 5
assert 0 < latency_ms < 100

# Avoid
assert result
assert results
```

## Troubleshooting

### Tests Fail with "Connection Refused"

Integration tests need external services:

```bash
# Start required services
docker run -d -p 6333:6333 qdrant/qdrant
# Start LM Studio or Ollama

# Then run tests
pytest tests/e2e/ --run-integration
```

### Tests Fail with "Permission Denied"

Deployment tests need proper permissions:

```bash
# Make scripts executable
chmod +x deployment/scripts/*.sh

# Run tests
pytest tests/e2e/test_deployment_workflow.py
```

### Async Tests Fail

Ensure pytest-asyncio is installed:

```bash
pip install pytest-asyncio
```

### Import Errors

Ensure you're running from project root:

```bash
cd /path/to/kb-rag-mcp
pytest tests/e2e/
```

## Performance Benchmarks

E2E tests also serve as performance benchmarks:

```bash
# Run with timing
pytest tests/e2e/ -v --durations=10

# Profile test execution
pytest tests/e2e/ --profile

# Memory profiling
pytest tests/e2e/ --memprof
```

## Future Enhancements

Planned additions:
- [ ] Search workflow E2E tests
- [ ] MCP server integration tests
- [ ] Performance regression tests
- [ ] Load testing scenarios
- [ ] Chaos engineering tests
- [ ] Multi-node deployment tests

## Contributing

When adding new E2E tests:

1. Follow existing structure
2. Add fixtures to `conftest.py` if reusable
3. Document test purpose in docstring
4. Mark integration tests appropriately
5. Update this README with new test categories

---

**Total Test Files:** 3  
**Total Test Classes:** 20  
**Total Tests:** 35+  
**Coverage:** Core E2E workflows  

*Last updated: v0.9.0 - 2026-05-15*
