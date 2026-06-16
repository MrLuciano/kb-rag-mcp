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


# ---------------------------------------------------------------------------
# Provider resilience metrics (PHASE 36)
# ---------------------------------------------------------------------------


def test_metrics_contains_provider_requests(client):
    """Test that response contains provider request metric."""
    response = client.get("/metrics")
    assert "kb_provider_requests_total" in response.text


def test_metrics_contains_provider_errors(client):
    """Test that response contains provider error metric."""
    response = client.get("/metrics")
    assert "kb_provider_errors_total" in response.text


def test_metrics_contains_provider_fallbacks(client):
    """Test that response contains provider fallback metric."""
    response = client.get("/metrics")
    assert "kb_provider_fallbacks_total" in response.text


def test_metrics_contains_provider_circuit_state(client):
    """Test that response contains provider circuit state gauge."""
    response = client.get("/metrics")
    assert "kb_provider_circuit_state" in response.text


def test_metrics_contains_provider_skipped_circuit_open(client):
    """Test that response contains circuit open skip metric."""
    response = client.get("/metrics")
    assert "kb_provider_skipped_circuit_open_total" in response.text


def test_metrics_contains_provider_skipped_budget_exhausted(client):
    """Test that response contains budget exhausted skip metric."""
    response = client.get("/metrics")
    assert "kb_provider_skipped_budget_exhausted_total" in response.text


def test_metrics_contains_provider_circuit_opened(client):
    """Test that response contains circuit opened metric."""
    response = client.get("/metrics")
    assert "kb_provider_circuit_opened_total" in response.text


def test_metrics_contains_help_for_provider_metrics(client):
    """Test that response contains HELP comments for provider metrics."""
    response = client.get("/metrics")
    assert "HELP kb_provider_requests_total" in response.text
    assert "HELP kb_provider_errors_total" in response.text
    assert "HELP kb_provider_circuit_state" in response.text
    assert "HELP kb_provider_fallbacks_total" in response.text


def test_provider_resilience_metrics_in_valid_format(client):
    """Test that provider metrics are parseable Prometheus format."""
    response = client.get("/metrics")

    # Parse the response - this will raise if format is invalid
    metrics = list(text_string_to_metric_families(response.text))
    metric_names = {m.name for m in metrics}

    # Note: parser strips _total suffix from Counter names
    assert "kb_provider_requests" in metric_names
    assert "kb_provider_errors" in metric_names
    assert "kb_provider_circuit_state" in metric_names
    assert "kb_provider_fallbacks" in metric_names
