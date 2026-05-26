"""
E2E test for Helm chart rendering and validation.

Validates that Helm chart templates render correctly with monitoring enabled.
"""
import subprocess
import yaml
import pytest
from pathlib import Path

CHART_PATH = Path("deployment/helm/kb-rag-mcp")

def helm_template(args=""):
    """Run helm template and return parsed YAML documents."""
    result = subprocess.run(
        f"helm template test-release {CHART_PATH} {args}",
        shell=True,
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )
    assert result.returncode == 0, f"helm template failed: {result.stderr}"
    # Parse multi-document YAML
    docs = list(yaml.safe_load_all(result.stdout))
    return [d for d in docs if d is not None]

def test_monitoring_enabled_by_default():
    """Monitoring stack is enabled by default."""
    docs = helm_template()
    prometheus_docs = [d for d in docs if d.get("metadata", {}).get("name", "").endswith("-prometheus")]
    grafana_docs = [d for d in docs if d.get("metadata", {}).get("name", "").endswith("-grafana")]
    assert len(prometheus_docs) > 0, "Prometheus resources not found"
    assert len(grafana_docs) > 0, "Grafana resources not found"

def test_monitoring_can_be_disabled():
    """Monitoring stack can be disabled via values."""
    docs = helm_template("--set monitoring.enabled=false")
    prometheus_docs = [d for d in docs if "prometheus" in d.get("metadata", {}).get("name", "")]
    grafana_docs = [d for d in docs if "grafana" in d.get("metadata", {}).get("name", "")]
    assert len(prometheus_docs) == 0, "Prometheus resources found when monitoring.enabled=false"
    assert len(grafana_docs) == 0, "Grafana resources found when monitoring.enabled=false"

def test_prometheus_statefulset_has_pvc():
    """Prometheus StatefulSet has volumeClaimTemplate."""
    docs = helm_template()
    prometheus_sts = [d for d in docs if d.get("kind") == "StatefulSet" and "prometheus" in d.get("metadata", {}).get("name", "")]
    assert len(prometheus_sts) == 1, "Prometheus StatefulSet not found"
    vct = prometheus_sts[0].get("spec", {}).get("volumeClaimTemplates", [])
    assert len(vct) > 0, "Prometheus StatefulSet missing volumeClaimTemplates"
    assert vct[0]["spec"]["resources"]["requests"]["storage"] == "10Gi"

def test_grafana_has_datasource_configmap():
    """Grafana datasource ConfigMap is created."""
    docs = helm_template()
    datasource_cm = [d for d in docs if d.get("kind") == "ConfigMap" and "grafana-datasources" in d.get("metadata", {}).get("name", "")]
    assert len(datasource_cm) == 1, "Grafana datasource ConfigMap not found"
    data = datasource_cm[0]["data"]["prometheus.yml"]
    assert "http://" in data and "prometheus" in data and ":9090" in data

def test_grafana_has_dashboard_configmap():
    """Grafana dashboard ConfigMap contains dashboard JSON."""
    docs = helm_template()
    dashboard_cm = [d for d in docs if d.get("kind") == "ConfigMap" and "grafana-dashboards" in d.get("metadata", {}).get("name", "") and "provisioning" not in d.get("metadata", {}).get("name", "")]
    assert len(dashboard_cm) == 1, "Grafana dashboard ConfigMap not found"
    assert "grafana-dashboard.json" in dashboard_cm[0]["data"]

def test_helm_lint_passes():
    """helm lint passes without errors."""
    result = subprocess.run(
        ["helm", "lint", str(CHART_PATH)],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"helm lint failed: {result.stderr}"
    assert "0 chart(s) failed" in result.stdout
