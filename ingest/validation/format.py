"""
File format validators.

Validates file extensions and MIME types.
"""

import mimetypes
from pathlib import Path
from typing import Optional, Set

from ingest.validation.base import (
    ValidationResult,
    ValidationSeverity,
    Validator,
)

# Supported file extensions (from ingest.py)
SUPPORTED_EXTENSIONS = {
    # Documents
    ".pdf",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ppt",
    # Text
    ".txt",
    ".md",
    ".rst",
    # Code
    ".py",
    ".ts",
    ".js",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".cs",
    # Config
    ".yaml",
    ".yml",
    ".json",
    ".xml",
    ".sh",
    ".sql",
}


class FileExtensionValidator(Validator):
    """
    Validates file extensions against a whitelist.

    Only allows files with recognized extensions to be processed.
    """

    def __init__(
        self,
        allowed_extensions: Optional[Set[str]] = None,
        name: str = "FileExtensionValidator",
    ):
        """
        Initialize validator.

        Args:
            allowed_extensions: Set of allowed extensions (e.g., {".pdf"})
                               Defaults to SUPPORTED_EXTENSIONS.
            name: Validator name
        """
        super().__init__(name)
        self.allowed_extensions = (
            allowed_extensions
            if allowed_extensions is not None
            else SUPPORTED_EXTENSIONS
        )

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate file extension."""
        extension = file_path.suffix.lower()

        if not extension:
            return ValidationResult.failure(
                self.name,
                f"File has no extension: {file_path.name}",
                ValidationSeverity.ERROR,
            )

        if extension not in self.allowed_extensions:
            return ValidationResult.failure(
                self.name,
                f"Unsupported file extension: {extension}",
                ValidationSeverity.ERROR,
            )

        return ValidationResult.success(
            self.name, f"Valid extension: {extension}"
        )


class MimeTypeValidator(Validator):
    """
    Validates MIME types for files.

    Checks that file MIME type matches expected types.
    """

    def __init__(
        self,
        allowed_mime_prefixes: Optional[Set[str]] = None,
        name: str = "MimeTypeValidator",
    ):
        """
        Initialize validator.

        Args:
            allowed_mime_prefixes: Set of allowed MIME type prefixes
                                  (e.g., {"text/", "application/"})
                                  Defaults to common document types.
            name: Validator name
        """
        super().__init__(name)
        self.allowed_mime_prefixes = allowed_mime_prefixes or {
            "text/",
            "application/",
            "image/",
        }

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate MIME type."""
        if not file_path.exists():
            return ValidationResult.failure(
                self.name,
                f"File not found: {file_path}",
                ValidationSeverity.ERROR,
            )

        # Guess MIME type from extension
        mime_type, _ = mimetypes.guess_type(str(file_path))

        if mime_type is None:
            return ValidationResult.failure(
                self.name,
                f"Could not determine MIME type for: {file_path.name}",
                ValidationSeverity.WARNING,
            )

        # Check if MIME type matches allowed prefixes
        if not any(
            mime_type.startswith(prefix)
            for prefix in self.allowed_mime_prefixes
        ):
            return ValidationResult.failure(
                self.name,
                f"Unsupported MIME type: {mime_type}",
                ValidationSeverity.ERROR,
            )

        return ValidationResult.success(
            self.name, f"Valid MIME type: {mime_type}"
        )


class FileExistsValidator(Validator):
    """Validates that file exists and is readable."""

    def __init__(self, name: str = "FileExistsValidator"):
        super().__init__(name)

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate file exists and is readable."""
        if not file_path.exists():
            return ValidationResult.failure(
                self.name,
                f"File not found: {file_path}",
                ValidationSeverity.ERROR,
            )

        if not file_path.is_file():
            return ValidationResult.failure(
                self.name,
                f"Path is not a file: {file_path}",
                ValidationSeverity.ERROR,
            )

        if not file_path.stat().st_size > 0:
            return ValidationResult.failure(
                self.name,
                f"File is empty: {file_path}",
                ValidationSeverity.WARNING,
            )

        # Try to read first byte to check readability
        try:
            with open(file_path, "rb") as f:
                f.read(1)
        except (PermissionError, OSError) as e:
            return ValidationResult.failure(
                self.name,
                f"File not readable: {file_path} ({e})",
                ValidationSeverity.ERROR,
            )

        return ValidationResult.success(self.name, "File exists and readable")
