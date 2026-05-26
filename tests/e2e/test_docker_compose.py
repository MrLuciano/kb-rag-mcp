"""
E2E test for Docker Compose deployment.

Validates that docker-compose.yml is valid and services are correctly defined.
"""
import subprocess
import pytest
import yaml
from pathlib import Path

COMPOSE_FILE = Path("docker-compose.yml")

def test_docker_compose_yaml_is_valid():
    """docker-compose.yml is valid YAML."""
    with open(COMPOSE_FILE) as f:
        config = yaml.safe_load(f)
    assert isinstance(config, dict)
    assert "services" in config

def test_required_services_defined():
    """All 4 required services are defined."""
    with open(COMPOSE_FILE) as f:
        config = yaml.safe_load(f)
    services = config["services"]
    required = ["qdrant", "kb-rag-mcp", "prometheus", "grafana"]
    for service in required:
        assert service in services, f"Missing service: {service}"

def test_prometheus_scrape_target():
    """Prometheus is configured to scrape kb-rag-mcp."""
    prom_config = Path("deployment/config/prometheus.yml")
    with open(prom_config) as f:
        config = yaml.safe_load(f)
    targets = config["scrape_configs"][0]["static_configs"][0]["targets"]
    assert "kb-rag-mcp:8000" in targets, f"Prometheus not scraping kb-rag-mcp, found: {targets}"

def test_grafana_datasource_provisioning():
    """Grafana datasource provisioning config exists."""
    ds_config = Path("deployment/config/grafana-provisioning/datasources/prometheus.yml")
    assert ds_config.exists(), "Datasource provisioning config missing"
    with open(ds_config) as f:
        config = yaml.safe_load(f)
    assert config["datasources"][0]["url"] == "http://prometheus:9090"

def test_grafana_dashboard_provisioning():
    """Grafana dashboard provisioning config exists."""
    db_config = Path("deployment/config/grafana-provisioning/dashboards/kb-rag.yml")
    assert db_config.exists(), "Dashboard provisioning config missing"
    with open(db_config) as f:
        config = yaml.safe_load(f)
    assert config["providers"][0]["options"]["path"] == "/etc/grafana/dashboards"

@pytest.mark.skipif(
    subprocess.run(["which", "docker-compose"], capture_output=True).returncode != 0,
    reason="docker-compose not installed"
)
def test_docker_compose_config_validates():
    """docker-compose config validates without errors."""
    result = subprocess.run(
        ["docker-compose", "config"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"docker-compose config failed: {result.stderr}"
