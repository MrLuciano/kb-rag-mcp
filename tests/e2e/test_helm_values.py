"""
E2E test for Helm chart values.yaml validation.

Validates that values.yaml contains required monitoring configuration.
"""
import yaml
import pytest
from pathlib import Path

VALUES_PATH = Path("deployment/helm/kb-rag-mcp/values.yaml")


def test_values_yaml_is_valid():
    """values.yaml is valid YAML."""
    with open(VALUES_PATH) as f:
        values = yaml.safe_load(f)
    assert values is not None, "values.yaml failed to parse"
    assert isinstance(values, dict), "values.yaml is not a dictionary"


def test_monitoring_enabled_key_exists():
    """monitoring.enabled key exists with default true."""
    with open(VALUES_PATH) as f:
        values = yaml.safe_load(f)
    assert "monitoring" in values, "monitoring section missing"
    assert "enabled" in values["monitoring"], "monitoring.enabled missing"
    assert values["monitoring"]["enabled"] is True, "monitoring.enabled should default to true"


def test_prometheus_enabled_key_exists():
    """prometheus.enabled key exists with default true."""
    with open(VALUES_PATH) as f:
        values = yaml.safe_load(f)
    assert "monitoring" in values, "monitoring section missing"
    assert "prometheus" in values["monitoring"], "monitoring.prometheus missing"
    assert "enabled" in values["monitoring"]["prometheus"], "prometheus.enabled missing"
    assert values["monitoring"]["prometheus"]["enabled"] is True, "prometheus.enabled should default to true"


def test_grafana_enabled_key_exists():
    """grafana.enabled key exists with default true."""
    with open(VALUES_PATH) as f:
        values = yaml.safe_load(f)
    assert "monitoring" in values, "monitoring section missing"
    assert "grafana" in values["monitoring"], "monitoring.grafana missing"
    assert "enabled" in values["monitoring"]["grafana"], "grafana.enabled missing"
    assert values["monitoring"]["grafana"]["enabled"] is True, "grafana.enabled should default to true"


def test_prometheus_retention_is_configurable():
    """prometheus.retention is configurable with default 15d."""
    with open(VALUES_PATH) as f:
        values = yaml.safe_load(f)
    assert "monitoring" in values, "monitoring section missing"
    assert "prometheus" in values["monitoring"], "monitoring.prometheus missing"
    assert "retention" in values["monitoring"]["prometheus"], "prometheus.retention missing"
    assert values["monitoring"]["prometheus"]["retention"] == "15d", "prometheus.retention should default to 15d"


def test_prometheus_storage_size_is_configurable():
    """prometheus.storage.size is configurable with default 10Gi."""
    with open(VALUES_PATH) as f:
        values = yaml.safe_load(f)
    assert "monitoring" in values, "monitoring section missing"
    assert "prometheus" in values["monitoring"], "monitoring.prometheus missing"
    assert "storage" in values["monitoring"]["prometheus"], "prometheus.storage missing"
    assert "size" in values["monitoring"]["prometheus"]["storage"], "prometheus.storage.size missing"
    assert values["monitoring"]["prometheus"]["storage"]["size"] == "10Gi", "prometheus.storage.size should default to 10Gi"
