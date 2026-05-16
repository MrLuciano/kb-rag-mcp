# Testing Policy for KB-RAG-MCP

## Test Strategy
- Use pytest for all unit, integration, and system tests
- Place all tests in the `tests/` directory
- All new features require tests for main success and common failure cases
- Target: 70% minimum coverage, 90% for critical code paths
- Test names must describe scenario and expected result
- Use fixtures via `conftest.py` for common test data/setup

## Running Tests
```
pytest tests
```

For continuous runs or checkpoint, use `pytest --maxfail=3 --disable-warnings -v`.

## Lint, Typing, Formatting
- Type checking via mypy (strict mode)
- Black + isort for formatting
- Lint via ruff or flake8 as enforced by CI

## Contribution
- All code must pass tests, type checks, and format/lint CI before merge
- Failing or missing tests must be explained in PR description

---
As the project evolves, update this document with new test conventions and required coverage per module.
