"""Tests for module classification inference."""

from pathlib import Path

import pytest

from ingest.classifier import MODULE_PATTERNS, infer_module


class TestInferModule:
    def test_known_product_directory_match(self):
        result = infer_module(
            Path("/docs/AppServer/admin/guide.pdf"),
            Path("/docs"),
        )
        assert result == "Administration"

    def test_known_product_config_directory(self):
        result = infer_module(
            Path("/docs/AppServer/configuration/settings.pdf"),
            Path("/docs"),
        )
        assert result == "Configuration"

    def test_known_product_api_directory(self):
        result = infer_module(
            Path("/docs/AppServer/api/reference.pdf"),
            Path("/docs"),
        )
        assert result == "API"

    def test_known_product_security_directory(self):
        result = infer_module(
            Path("/docs/AppServer/security/auth_guide.pdf"),
            Path("/docs"),
        )
        assert result == "Security"

    def test_datasync_connector_directory(self):
        result = infer_module(
            Path("/docs/DataSync/connectors/sap_connector.pdf"),
            Path("/docs"),
        )
        assert result == "Connectors"

    def test_datasync_monitoring_directory(self):
        result = infer_module(
            Path("/docs/DataSync/monitoring/dashboard.pdf"),
            Path("/docs"),
        )
        assert result == "Monitoring"

    def test_adminportal_users_directory(self):
        result = infer_module(
            Path("/docs/AdminPortal/users/user_guide.pdf"),
            Path("/docs"),
        )
        assert result == "User Management"

    def test_adminportal_roles_directory(self):
        result = infer_module(
            Path("/docs/AdminPortal/roles/admin_guide.pdf"),
            Path("/docs"),
        )
        assert result == "Roles & Permissions"

    def test_adminportal_reporting_directory(self):
        result = infer_module(
            Path("/docs/AdminPortal/reporting/analytics.pdf"),
            Path("/docs"),
        )
        assert result == "Reporting"

    def test_known_product_no_match(self):
        result = infer_module(
            Path("/docs/AppServer/readme.txt"),
            Path("/docs"),
        )
        assert result == ""

    def test_unknown_product(self):
        result = infer_module(
            Path("/docs/UnknownProduct/guide.pdf"),
            Path("/docs"),
        )
        assert result == ""

    def test_file_not_under_docs_root(self):
        result = infer_module(
            Path("/some/other/path/file.pdf"),
            Path("/docs"),
        )
        assert result == ""

    def test_no_match_when_only_filename_pattern(self):
        result = infer_module(
            Path("/docs/AppServer/api_guide.pdf"),
            Path("/docs"),
        )
        assert result == ""

    def test_MODULE_PATTERNS_structure(self):
        assert "AppServer" in MODULE_PATTERNS
        assert "DataSync" in MODULE_PATTERNS
        assert "AdminPortal" in MODULE_PATTERNS
        for product, patterns in MODULE_PATTERNS.items():
            for pattern_str, module_name in patterns:
                assert isinstance(pattern_str, str)
                assert isinstance(module_name, str)
                assert len(module_name) > 0

    def test_infer_module_is_importable(self):
        from inspect import isfunction
        assert isfunction(infer_module)
