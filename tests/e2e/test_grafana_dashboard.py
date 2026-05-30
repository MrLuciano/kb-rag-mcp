"""
E2E test for Grafana dashboard JSON structure.

Validates that the dashboard definition is valid and complete.
"""
import json
import pytest
from pathlib import Path

DASHBOARD_PATH = Path("deployment/config/grafana-dashboard.json")


def test_dashboard_json_is_valid():
    """Dashboard JSON is valid and parseable."""
    with open(DASHBOARD_PATH) as f:
        dashboard = json.load(f)
    assert isinstance(dashboard, dict)
    assert "panels" in dashboard


def test_dashboard_has_rows():
    """Dashboard has at least 1 row section."""
    with open(DASHBOARD_PATH) as f:
        dashboard = json.load(f)
    rows = [p for p in dashboard["panels"] if p.get("type") == "row"]
    assert len(rows) >= 1, f"Expected ≥1 rows, found {len(rows)}"


def test_dashboard_has_minimum_panels():
    """Dashboard has at least 5 metric panels (excluding rows)."""
    with open(DASHBOARD_PATH) as f:
        dashboard = json.load(f)
    panels = [p for p in dashboard["panels"] if p.get("type") != "row"]
    assert len(panels) >= 5, f"Expected ≥5 panels, found {len(panels)}"


def test_dashboard_refresh_intervals():
    """Dashboard supports required refresh intervals."""
    with open(DASHBOARD_PATH) as f:
        dashboard = json.load(f)
    intervals = dashboard.get("timepicker", {}).get("refresh_intervals", [])
    required = ["5s", "15s", "30s", "1m"]
    for interval in required:
        assert interval in intervals, f"Missing refresh interval: {interval}"


def test_dashboard_panels_have_queries():
    """All non-row panels have Prometheus query targets."""
    with open(DASHBOARD_PATH) as f:
        dashboard = json.load(f)
    panels = [p for p in dashboard["panels"] if p.get("type") != "row"]
    for panel in panels:
        targets = panel.get("targets", [])
        assert len(targets) > 0, f"Panel '{panel.get('title')}' has no targets"
        for target in targets:
            assert "expr" in target or "datasource" in target, \
                f"Panel '{panel.get('title')}' target missing expr/datasource"
