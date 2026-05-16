"""
Extract version information from filenames and paths.

Supports common version patterns found in documentation:
- Numeric: 22.3, 16.2.1
- CE prefix: CE 24.4, CE 23.1
- v prefix: v2.5, v1.0.0

Version is extracted from:
1. Filename (highest priority)
2. Parent directory name
3. Grandparent directory name

The first match is used as the version.

Examples:
    >>> extractor = VersionExtractor()
    >>> extractor.extract(Path("/docs/ArchiveCenter_22.3_Admin.pdf"))
    "22.3"
    >>> extractor.extract(Path("/docs/xECM/CE 24.4/manual.pdf"))
    "CE 24.4"
    >>> extractor.extract(Path("/docs/Release Notes for version 16.2.pdf"))
    "16.2"
    >>> extractor.extract(Path("/docs/file_without_version.pdf"))
    None
"""

import logging
import re
from pathlib import Path

log = logging.getLogger("kb-ingest.version")


class VersionExtractor:
    """Extract version info from filenames and paths."""

    # Regex patterns for version detection (priority order)
    PATTERNS = [
        # CE prefix: "CE 24.4", "CE 23.1"
        r"CE\s+(\d{2}\.\d+(?:\.\d+)?)",
        # v prefix: "v2.5", "v1.0.0"
        r"v(\d+\.\d+(?:\.\d+)?)",
        # Numeric: "22.3", "16.2.1"
        r"(\d{2}\.\d+(?:\.\d+)?)",
        # Version keyword: "version 16.2"
        r"version\s+(\d+\.\d+(?:\.\d+)?)",
    ]

    def extract(self, file_path: Path) -> str | None:
        """
        Extract version from file path.

        Checks filename first, then parent directories.

        Args:
            file_path: Path to document file

        Returns:
            Version string or None if not found
        """
        # Sources to check (priority order)
        sources = [
            file_path.name,  # filename
            file_path.parent.name,  # parent dir
            file_path.parent.parent.name,  # grandparent dir
        ]

        for source in sources:
            for pattern in self.PATTERNS:
                match = re.search(pattern, source, re.IGNORECASE)
                if match:
                    # Get the full match (includes prefix like CE, v)
                    version = match.group(0)
                    log.debug(
                        f"Extracted version '{version}' from '{source}'"
                    )
                    return version

        log.debug(f"No version found in path: {file_path}")
        return None

    def extract_batch(
        self, file_paths: list[Path]
    ) -> dict[Path, str | None]:
        """
        Extract versions for multiple files.

        Args:
            file_paths: List of file paths

        Returns:
            Dict mapping path to version (or None)
        """
        return {path: self.extract(path) for path in file_paths}


# Singleton instance for convenience
_extractor = VersionExtractor()


def extract_version(file_path: Path) -> str | None:
    """
    Convenience function to extract version from path.

    Args:
        file_path: Path to document file

    Returns:
        Version string or None if not found
    """
    return _extractor.extract(file_path)
