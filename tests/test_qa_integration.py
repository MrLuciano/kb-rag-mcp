import pytest

pytest.skip(
    "QA integration test is skipped by default. Remove this skip to run full pipeline.",
    allow_module_level=True,
)


def test_pipeline_otcs():
    # This will eventually call qa/run_qa.py against the QA fixtures and corpus
    assert True  # Replace with pipeline invocation & assertions
