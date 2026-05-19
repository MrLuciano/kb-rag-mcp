"""
E2E tests for deployment and operations.

Tests deployment scripts, backup/restore, and operational workflows.
"""

import os
import subprocess
import tempfile
from pathlib import Path
import pytest
import tarfile
import shutil


class TestBackupRestore:
    """Test backup and restore operations."""
    
    def test_backup_creation(self, tmp_path: Path):
        """Test backup creation creates valid tarball."""
        # Create mock data directory
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        # Create mock files
        (data_dir / "jobs.db").write_text("mock database")
        (data_dir / "kb_metadata.db").write_text("mock metadata")
        
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "kb-rag.env").write_text("MOCK_CONFIG=1")
        
        # Create backup
        backup_path = tmp_path / "backup.tar.gz"
        
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(data_dir, arcname="data")
            tar.add(config_dir, arcname="config")
        
        assert backup_path.exists()
        assert backup_path.stat().st_size > 0
        
        # Verify tarball contents
        with tarfile.open(backup_path, "r:gz") as tar:
            members = tar.getnames()
            assert "data/jobs.db" in members
            assert "data/kb_metadata.db" in members
            assert "config/kb-rag.env" in members
    
    def test_backup_restore_integrity(self, tmp_path: Path):
        """Test restored backup matches original."""
        # Create original data
        original_dir = tmp_path / "original"
        original_dir.mkdir()
        
        data_content = "test database content"
        (original_dir / "test.db").write_text(data_content)
        
        # Create backup
        backup_path = tmp_path / "backup.tar.gz"
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(original_dir / "test.db", arcname="test.db")
        
        # Restore to new location
        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()
        
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(restore_dir)
        
        # Verify integrity
        restored_content = (restore_dir / "test.db").read_text()
        assert restored_content == data_content
    
    def test_backup_with_compression(self, tmp_path: Path):
        """Test backup compression reduces file size."""
        # Create large file
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        large_content = "A" * 10000  # 10KB of repeated data
        (data_dir / "large.db").write_text(large_content)
        
        # Create uncompressed tar
        uncompressed_path = tmp_path / "uncompressed.tar"
        with tarfile.open(uncompressed_path, "w") as tar:
            tar.add(data_dir, arcname="data")
        
        # Create compressed tar
        compressed_path = tmp_path / "compressed.tar.gz"
        with tarfile.open(compressed_path, "w:gz") as tar:
            tar.add(data_dir, arcname="data")
        
        # Verify compression works
        uncompressed_size = uncompressed_path.stat().st_size
        compressed_size = compressed_path.stat().st_size
        
        assert compressed_size < uncompressed_size
        # Should achieve significant compression on repeated data
        assert compressed_size < uncompressed_size * 0.5


class TestConfigurationValidation:
    """Test configuration file validation."""
    
    def test_env_template_complete(self):
        """Test .env.template has all required variables."""
        template_path = Path("deployment/config/kb-rag.env.template")
        
        if not template_path.exists():
            pytest.skip("Template not found")
        
        content = template_path.read_text()
        
        # Required variables
        required_vars = [
            "EMBED_URL",
            "QDRANT_URL",
            "COLLECTION_NAME",
            "HEALTH_PORT",
            "LOG_LEVEL",
        ]
        
        for var in required_vars:
            assert var in content, f"Missing required variable: {var}"
    
    def test_systemd_service_files_exist(self):
        """Test systemd service files exist."""
        systemd_dir = Path("deployment/systemd")
        
        if not systemd_dir.exists():
            pytest.skip("Systemd directory not found")
        
        required_files = [
            "kb-rag-server.service",
            "kb-rag-health.service",
            "kb-rag-scheduler.service",
            "kb-rag.target",
        ]
        
        for filename in required_files:
            file_path = systemd_dir / filename
            assert file_path.exists(), f"Missing service file: {filename}"
    
    def test_systemd_service_syntax(self):
        """Test systemd service files have valid syntax."""
        systemd_dir = Path("deployment/systemd")
        
        if not systemd_dir.exists():
            pytest.skip("Systemd directory not found")
        
        service_file = systemd_dir / "kb-rag-server.service"
        if not service_file.exists():
            pytest.skip("Service file not found")
        
        content = service_file.read_text()
        
        # Check for required sections
        assert "[Unit]" in content
        assert "[Service]" in content
        assert "[Install]" in content
        
        # Check for required fields
        assert "Description=" in content
        assert "ExecStart=" in content
        assert "User=" in content


class TestScriptValidation:
    """Test deployment script validation."""
    
    def test_install_script_exists(self):
        """Test install.sh exists and is executable."""
        script_path = Path("deployment/scripts/install.sh")
        
        if not script_path.exists():
            pytest.skip("Install script not found")
        
        assert script_path.exists()
        # Check if executable bit is set
        assert os.access(script_path, os.X_OK)
    
    def test_backup_script_exists(self):
        """Test backup.sh exists and is executable."""
        script_path = Path("deployment/scripts/backup.sh")
        
        if not script_path.exists():
            pytest.skip("Backup script not found")
        
        assert script_path.exists()
        assert os.access(script_path, os.X_OK)
    
    def test_health_check_script_exists(self):
        """Test health-check.sh exists."""
        script_path = Path("deployment/scripts/health-check.sh")
        
        if not script_path.exists():
            pytest.skip("Health check script not found")
        
        assert script_path.exists()
    
    def test_script_shebang(self):
        """Test scripts have correct shebang."""
        scripts_dir = Path("deployment/scripts")
        
        if not scripts_dir.exists():
            pytest.skip("Scripts directory not found")
        
        for script_path in scripts_dir.glob("*.sh"):
            content = script_path.read_text()
            first_line = content.split('\n')[0]
            
            # Should start with #!/bin/bash or #!/usr/bin/env bash
            assert first_line.startswith("#!/"), \
                f"{script_path.name} missing shebang"
            assert "bash" in first_line, \
                f"{script_path.name} not a bash script"


class TestDirectoryStructure:
    """Test expected directory structure."""
    
    def test_deployment_structure(self):
        """Test deployment directory structure."""
        base_dir = Path("deployment")
        
        if not base_dir.exists():
            pytest.skip("Deployment directory not found")
        
        expected_dirs = [
            "scripts",
            "systemd",
            "config",
        ]
        
        for dirname in expected_dirs:
            dir_path = base_dir / dirname
            assert dir_path.exists(), f"Missing directory: {dirname}"
            assert dir_path.is_dir()
    
    def test_project_root_structure(self):
        """Test project root has expected directories."""
        expected_dirs = [
            "ingest",
            "server",
            "tests",
            "docs",
        ]
        
        for dirname in expected_dirs:
            dir_path = Path(dirname)
            assert dir_path.exists(), f"Missing directory: {dirname}"
            assert dir_path.is_dir()


class TestHealthCheckIntegration:
    """Test health check integration with deployment."""
    
    def test_health_server_module_exists(self):
        """Test health server module exists."""
        module_path = Path("server/health_server.py")
        assert module_path.exists()
        
        # Check it's importable
        try:
            import kb_server.health_server
        except ImportError as e:
            pytest.fail(f"Cannot import health_server: {e}")
    
    def test_health_module_exists(self):
        """Test health check module exists."""
        module_path = Path("server/health.py")
        assert module_path.exists()
        
        try:
            import kb_server.health
        except ImportError as e:
            pytest.fail(f"Cannot import health: {e}")


class TestLogRotation:
    """Test log rotation configuration."""
    
    def test_logrotate_config_exists(self):
        """Test logrotate configuration exists."""
        config_path = Path("deployment/config/kb-rag-logrotate.conf")
        
        if not config_path.exists():
            pytest.skip("Logrotate config not found")
        
        assert config_path.exists()
        
        content = config_path.read_text()
        
        # Check for key directives
        assert "rotate" in content
        assert "compress" in content
        assert "daily" in content or "weekly" in content


class TestPrometheusConfig:
    """Test Prometheus configuration."""
    
    def test_prometheus_config_exists(self):
        """Test Prometheus config exists."""
        config_path = Path("deployment/config/prometheus.yml")
        
        if not config_path.exists():
            pytest.skip("Prometheus config not found")
        
        assert config_path.exists()
    
    def test_alert_rules_exist(self):
        """Test Prometheus alert rules exist."""
        rules_path = Path("deployment/config/kb-rag-alerts.yml")
        
        if not rules_path.exists():
            pytest.skip("Alert rules not found")
        
        assert rules_path.exists()
        
        content = rules_path.read_text()
        
        # Should have alert rules
        assert "groups:" in content
        assert "alert:" in content


@pytest.mark.skipif(
    os.getenv("SKIP_DEPLOYMENT_TESTS") == "1",
    reason="Deployment tests disabled"
)
class TestRealDeployment:
    """
    Integration tests for real deployment operations.
    
    These tests should be run in isolated environments only.
    Requires root/sudo access.
    """
    
    def test_install_script_dry_run(self):
        """Test install script in dry-run mode."""
        pytest.skip("Requires isolated environment and sudo")
    
    def test_backup_restore_workflow(self):
        """Test complete backup and restore workflow."""
        pytest.skip("Requires deployed system")
    
    def test_update_script(self):
        """Test update script workflow."""
        pytest.skip("Requires deployed system")


class TestGrafanaDashboard:
    """Test Grafana dashboard configuration."""

    def test_grafana_dashboard_exists(self):
        """Grafana dashboard JSON file must exist and be valid."""
        import json
        dashboard_path = Path("deployment/config/grafana-dashboard.json")
        assert dashboard_path.exists(), "grafana-dashboard.json not found"
        with open(dashboard_path) as f:
            data = json.load(f)
        assert "panels" in data, "Dashboard must have panels"
        assert "title" in data, "Dashboard must have title"
        assert len(data["panels"]) > 5, "Dashboard should have at least 6 panels"


class TestSecurityDoc:
    """Test security documentation exists and covers required topics."""

    def test_security_doc_exists(self):
        """SECURITY.md must exist and cover key topics."""
        security_path = Path("docs/SECURITY.md")
        assert security_path.exists(), "docs/SECURITY.md not found"
        content = security_path.read_text()
        for topic in ["threat", "authentication", "network", "hardening"]:
            assert topic.lower() in content.lower(), \
                f"SECURITY.md should cover '{topic}'"
