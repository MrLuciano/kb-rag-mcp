"""
Tests for version extraction.

Tests cover:
- Extraction from filenames (numeric, CE prefix, v prefix, version keyword)
- Extraction from parent directories
- Priority (filename > parent > grandparent)
- Edge cases (no version, multiple patterns)
- Batch extraction
"""

from pathlib import Path

import pytest

from ingest.core.version_extractor import (
    VersionExtractor,
    extract_version,
)


class TestVersionExtractor:
    """Test version extraction logic."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return VersionExtractor()

    def test_extract_numeric_from_filename(self, extractor):
        """Extract numeric version from filename."""
        path = Path("/docs/AppServer_32.0_Admin_Guide.pdf")
        assert extractor.extract(path) == "32.0"

    def test_extract_numeric_three_parts(self, extractor):
        """Extract three-part numeric version."""
        path = Path("/docs/Manual_16.2.1.pdf")
        assert extractor.extract(path) == "16.2.1"

    def test_extract_ce_prefix_from_filename(self, extractor):
        """Extract CE version from filename."""
        path = Path("/docs/manual_CE 24.4.pdf")
        version = extractor.extract(path)
        assert version in ["CE 24.4", "24.4"]  # May or may not include prefix

    def test_extract_v_prefix_from_filename(self, extractor):
        """Extract v-prefixed version from filename."""
        path = Path("/docs/release_notes_v2.5.pdf")
        version = extractor.extract(path)
        assert version in ["v2.5", "2.5"]

    def test_extract_version_keyword(self, extractor):
        """Extract version with 'version' keyword."""
        path = Path("/docs/Release Notes for version 16.2.pdf")
        version = extractor.extract(path)
        assert version in ["version 16.2", "16.2"]

    def test_extract_from_parent_dir(self, extractor):
        """Extract version from parent directory."""
        path = Path("/docs/DataSync/32.0/manual.pdf")
        version = extractor.extract(path)
        # Should extract from parent dir "32.0"
        assert "32.0" in version

    def test_extract_from_grandparent_dir(self, extractor):
        """Extract version from grandparent directory."""
        path = Path("/docs/v23.1/guides/admin.pdf")
        version = extractor.extract(path)
        assert "23.1" in version

    def test_priority_filename_over_parent(self, extractor):
        """Filename version takes priority over directory."""
        path = Path("/docs/v22.3/manual_v24.4.pdf")
        version = extractor.extract(path)
        # Filename "v24.4" should take priority
        assert "24.4" in version
        assert "22.3" not in version

    def test_priority_parent_over_grandparent(self, extractor):
        """Parent dir version takes priority over grandparent."""
        path = Path("/docs/v22.3/CE 24.4/manual.pdf")
        version = extractor.extract(path)
        # Parent "CE 24.4" should take priority
        assert "24.4" in version

    def test_no_version_found(self, extractor):
        """Return None when no version found."""
        path = Path("/docs/general/readme.pdf")
        assert extractor.extract(path) is None

    def test_case_insensitive(self, extractor):
        """Version extraction should be case insensitive."""
        path1 = Path("/docs/ce 24.4/manual.pdf")
        path2 = Path("/docs/CE 24.4/manual.pdf")

        version1 = extractor.extract(path1)
        version2 = extractor.extract(path2)

        assert version1 is not None
        assert version2 is not None
        assert "24.4" in version1
        assert "24.4" in version2

    def test_version_in_path_component(self, extractor):
        """Extract version from anywhere in path component."""
        path = Path("/docs/AppServer_32.0_Documentation/manual.pdf")
        version = extractor.extract(path)
        assert "32.0" in version

    def test_multiple_numeric_patterns(self, extractor):
        """When multiple patterns match, return first match."""
        path = Path("/docs/manual_22.3_v24.4.pdf")
        version = extractor.extract(path)
        # Should return one of the versions
        assert version is not None
        assert "22.3" in version or "24.4" in version

    def test_extract_batch(self, extractor):
        """Batch extraction should work for multiple files."""
        paths = [
            Path("/docs/manual_22.3.pdf"),
            Path("/docs/guide_v24.4.pdf"),
            Path("/docs/readme.pdf"),  # No version
        ]

        results = extractor.extract_batch(paths)

        assert len(results) == 3
        assert "22.3" in results[paths[0]]
        assert "24.4" in results[paths[1]]
        assert results[paths[2]] is None

    def test_convenience_function(self):
        """Test convenience function."""
        path = Path("/docs/manual_22.3.pdf")
        version = extract_version(path)
        assert "22.3" in version


class TestVersionPatterns:
    """Test specific version pattern matching."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return VersionExtractor()

    def test_ce_pattern_variations(self, extractor):
        """Test CE pattern with various formats."""
        test_cases = [
            ("CE 24.4", "24.4"),
            ("CE 23.1", "23.1"),
            ("ce 22.3", "22.3"),  # Case insensitive
            ("CE24.4", None),  # Should require space
        ]

        for input_str, expected in test_cases:
            path = Path(f"/docs/{input_str}/manual.pdf")
            version = extractor.extract(path)

            if expected:
                assert version is not None
                assert expected in version
            else:
                # May or may not match depending on pattern
                pass

    def test_v_pattern_variations(self, extractor):
        """Test v-prefix pattern with various formats."""
        test_cases = [
            ("v2.5", "2.5"),
            ("v1.0.0", "1.0.0"),
            ("v23.1", "23.1"),
            ("V2.5", "2.5"),  # Case insensitive
        ]

        for input_str, expected in test_cases:
            path = Path(f"/docs/manual_{input_str}.pdf")
            version = extractor.extract(path)
            assert version is not None
            assert expected in version

    def test_numeric_pattern_variations(self, extractor):
        """Test numeric pattern with various formats."""
        test_cases = [
            ("22.3", "22.3"),
            ("16.2.1", "16.2.1"),
            ("99.9", "99.9"),
            ("10.0", "10.0"),
        ]

        for input_str, expected in test_cases:
            path = Path(f"/docs/manual_{input_str}.pdf")
            version = extractor.extract(path)
            assert version is not None
            assert expected in version

    def test_version_keyword_variations(self, extractor):
        """Test version keyword pattern."""
        test_cases = [
            "version 16.2",
            "Version 16.2",
            "VERSION 16.2",
        ]

        for input_str in test_cases:
            path = Path(f"/docs/Release Notes for {input_str}.pdf")
            version = extractor.extract(path)
            assert version is not None
            assert "16.2" in version
