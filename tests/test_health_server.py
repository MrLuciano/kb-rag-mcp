"""
Tests for health_server.py metrics endpoint.

Verifies that the /metrics endpoint exposes Prometheus metrics correctly.
"""

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from kb_server.health_server import app


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


def test_metrics_endpoint_returns_200(client):
    """Test that /metrics endpoint returns HTTP 200."""
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_endpoint_content_type(client):
    """Test that /metrics returns correct Prometheus Content-Type."""
    response = client.get("/metrics")
    # Prometheus text format content type (accept both 0.0.4 and 1.0.0)
    content_type = response.headers["content-type"]
    assert content_type.startswith("text/plain; version=")
    assert "charset=utf-8" in content_type


def test_metrics_contains_ingest_job_metric(client):
    """Test that response contains job creation metric."""
    response = client.get("/metrics")
    assert "kb_ingest_jobs_created_total" in response.text


def test_metrics_contains_cache_metric(client):
    """Test that response contains cache hit metric."""
    response = client.get("/metrics")
    assert "kb_rag_cache_hits_total" in response.text


def test_metrics_contains_help_and_type_comments(client):
    """Test that response contains Prometheus metadata comments."""
    response = client.get("/metrics")
    assert "# HELP" in response.text
    assert "# TYPE" in response.text


def test_metrics_response_is_valid_prometheus_format(client):
    """Test that response is parseable as Prometheus text format."""
    response = client.get("/metrics")
    
    # Parse the response - this will raise if format is invalid
    metrics = list(text_string_to_metric_families(response.text))
    
    # Should have multiple metric families
    assert len(metrics) > 0
    
    # Check for expected metric declarations in raw text
    # (Counter metrics with labels won't have data points until used)
    assert "# TYPE kb_ingest_jobs_created_total counter" in response.text
    assert "# TYPE kb_rag_cache_hits_total counter" in response.text
