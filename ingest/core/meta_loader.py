"""
Load and apply metadata overrides from _meta.json files.

Supports directory-level defaults and file-specific overrides:

_meta.json schema:
{
  "product": "DefaultProduct",
  "doc_type": "default_doc_type",
  "files": {
    "specific_file.pdf": {
      "product": "OverrideProduct",
      "doc_type": "api_guide"
    }
  }
}

Precedence (highest to lowest):
1. File-specific override in _meta.json
2. Directory-level default in _meta.json
3. Auto-classification from metadata.py

Validation:
- product: must exist (any string allowed)
- doc_type: must be in VALID_DOC_TYPES list

Usage:
    >>> loader = MetaLoader()
    >>> meta = loader.load_meta(Path("/docs/DataSync"))
    >>> overrides = loader.get_metadata(
    ...     Path("/docs/DataSync/manual.pdf"),
    ...     meta
    ... )
"""

import json
import logging
from pathlib import Path
from typing import cast

log = logging.getLogger("kb-ingest.meta")


class MetaLoader:
    """Load metadata overrides from _meta.json files."""

    META_FILENAME = "_meta.json"

    # Valid doc_type values (must match classifier.py)
    VALID_DOC_TYPES = [
        "admin_guide",
        "install_guide",
        "upgrade_guide",
        "config_guide",
        "user_guide",
        "api_guide",
        "release_notes",
        "howto",
        "training",
        "overview",
        "reference",
        "standard",
        "meeting",
        "release_artifact",
        "document",
    ]

    def load_meta(self, directory: Path) -> dict:
        """
        Load _meta.json from directory.

        Args:
            directory: Directory to search for _meta.json

        Returns:
            Metadata dict (empty if file doesn't exist)

        Raises:
            ValueError: If metadata schema is invalid
        """
        meta_file = directory / self.META_FILENAME

        if not meta_file.exists():
            return {}

        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {meta_file}: {e}") from e

        # Validate schema
        self._validate_meta(meta, meta_file)

        log.info(f"Loaded metadata overrides from {meta_file}")
        return cast(dict, meta)

    def _validate_meta(self, meta: dict, meta_file: Path):
        """
        Validate _meta.json schema.

        Args:
            meta: Loaded metadata dict
            meta_file: Path to _meta.json (for error messages)

        Raises:
            ValueError: If schema is invalid
        """
        # Validate directory-level doc_type
        if "doc_type" in meta:
            if meta["doc_type"] not in self.VALID_DOC_TYPES:
                raise ValueError(
                    f"Invalid doc_type in {meta_file}: "
                    f"{meta['doc_type']} (must be one of "
                    f"{', '.join(self.VALID_DOC_TYPES)})"
                )

        # Validate file-specific overrides
        if "files" in meta:
            if not isinstance(meta["files"], dict):
                raise ValueError(f"'files' must be a dict in {meta_file}")

            for filename, overrides in meta["files"].items():
                if not isinstance(overrides, dict):
                    raise ValueError(
                        f"Overrides for '{filename}' must be a dict"
                    )

                if "doc_type" in overrides:
                    if overrides["doc_type"] not in self.VALID_DOC_TYPES:
                        raise ValueError(
                            f"Invalid doc_type for '{filename}' in "
                            f"{meta_file}: {overrides['doc_type']}"
                        )

    def get_metadata(self, file_path: Path, meta: dict) -> dict:
        """
        Get metadata for file considering precedence.

        Args:
            file_path: File to get metadata for
            meta: Loaded _meta.json dict

        Returns:
            Dict with 'product', 'doc_type', 'vendor', 'subsystem'
            (or None if not set)
        """
        filename = file_path.name

        # File-specific override (highest priority)
        if "files" in meta and filename in meta["files"]:
            file_meta = meta["files"][filename]

            # File-specific overrides, fallback to directory defaults
            return {
                "product": file_meta.get("product", meta.get("product")),
                "doc_type": file_meta.get("doc_type", meta.get("doc_type")),
                "vendor": file_meta.get("vendor", meta.get("vendor")),
                "subsystem": file_meta.get("subsystem", meta.get("subsystem")),
            }

        # Directory-level defaults
        return {
            "product": meta.get("product"),
            "doc_type": meta.get("doc_type"),
            "vendor": meta.get("vendor"),
            "subsystem": meta.get("subsystem"),
        }

    def scan_directory(self, directory: Path) -> dict[Path, dict]:
        """
        Load all _meta.json files in directory tree.

        Args:
            directory: Root directory to scan

        Returns:
            Dict mapping directory path to loaded metadata
        """
        meta_map = {}

        for meta_file in directory.rglob(self.META_FILENAME):
            dir_path = meta_file.parent
            try:
                meta_map[dir_path] = self.load_meta(dir_path)
            except Exception as e:
                log.error(f"Failed to load {meta_file}: {e}")

        log.info(f"Loaded {len(meta_map)} _meta.json files from {directory}")
        return meta_map


# Singleton instance for convenience
_loader = MetaLoader()


def load_directory_meta(directory: Path) -> dict:
    """
    Convenience function to load _meta.json from directory.

    Args:
        directory: Directory containing _meta.json

    Returns:
        Metadata dict (empty if file doesn't exist)
    """
    return _loader.load_meta(directory)


def get_file_metadata(file_path: Path, meta: dict) -> dict:
    """
    Convenience function to get metadata for file.

    Args:
        file_path: File to get metadata for
        meta: Loaded _meta.json dict

    Returns:
        Dict with 'product' and 'doc_type' (or None if not set)
    """
    return _loader.get_metadata(file_path, meta)
