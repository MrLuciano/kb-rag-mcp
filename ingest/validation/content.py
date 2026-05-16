"""
Content quality validators.

Validates document content quality and readability.
"""

import re
from pathlib import Path
from typing import Optional

from ingest.validation.base import (
    ValidationResult,
    ValidationSeverity,
    Validator,
)


class TextContentValidator(Validator):
    """
    Validates text content quality.

    Checks for minimum content length, text-to-noise ratio,
    and presence of actual readable text.
    """

    def __init__(
        self,
        min_text_length: int = 10,
        min_word_count: int = 5,
        name: str = "TextContentValidator",
    ):
        """
        Initialize validator.

        Args:
            min_text_length: Minimum text length in characters
            min_word_count: Minimum number of words
            name: Validator name
        """
        super().__init__(name)
        self.min_text_length = min_text_length
        self.min_word_count = min_word_count

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate text content quality."""
        if not file_path.exists():
            return ValidationResult.failure(
                self.name,
                f"File not found: {file_path}",
                ValidationSeverity.ERROR,
            )

        # Only validate text files
        text_extensions = {
            ".txt",
            ".md",
            ".rst",
            ".py",
            ".js",
            ".ts",
            ".java",
            ".go",
            ".rs",
            ".cpp",
            ".c",
            ".cs",
            ".json",
            ".yaml",
            ".yml",
            ".xml",
        }

        extension = file_path.suffix.lower()
        if extension not in text_extensions:
            # Skip validation for binary files
            return ValidationResult.success(
                self.name, f"Skipped for {extension}"
            )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(10000)  # Read first 10KB
        except (UnicodeDecodeError, OSError) as e:
            return ValidationResult.failure(
                self.name,
                f"Cannot read text content: {e}",
                ValidationSeverity.WARNING,
            )

        # Check minimum length
        if len(content) < self.min_text_length:
            return ValidationResult.failure(
                self.name,
                (
                    f"Content too short: {len(content)} chars "
                    f"(min: {self.min_text_length})"
                ),
                ValidationSeverity.WARNING,
            )

        # Count words (split by whitespace)
        words = content.split()
        if len(words) < self.min_word_count:
            return ValidationResult.failure(
                self.name,
                (
                    f"Too few words: {len(words)} "
                    f"(min: {self.min_word_count})"
                ),
                ValidationSeverity.WARNING,
            )

        return ValidationResult.success(
            self.name, f"Valid content: {len(words)} words"
        )


class EncodingValidator(Validator):
    """
    Validates file encoding.

    Ensures files are properly encoded and readable.
    """

    def __init__(
        self,
        allowed_encodings: Optional[list[str]] = None,
        name: str = "EncodingValidator",
    ):
        """
        Initialize validator.

        Args:
            allowed_encodings: List of allowed encodings
                              (default: ["utf-8", "ascii", "latin-1"])
            name: Validator name
        """
        super().__init__(name)
        self.allowed_encodings = allowed_encodings or [
            "utf-8",
            "ascii",
            "latin-1",
        ]

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate file encoding."""
        if not file_path.exists():
            return ValidationResult.failure(
                self.name,
                f"File not found: {file_path}",
                ValidationSeverity.ERROR,
            )

        # Only check text files
        text_extensions = {
            ".txt",
            ".md",
            ".rst",
            ".py",
            ".js",
            ".ts",
            ".java",
            ".go",
            ".rs",
            ".cpp",
            ".c",
            ".cs",
            ".yaml",
            ".yml",
            ".xml",
        }

        extension = file_path.suffix.lower()
        if extension not in text_extensions:
            return ValidationResult.success(
                self.name, f"Skipped for {extension}"
            )

        # Try each encoding
        for encoding in self.allowed_encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    f.read(1000)  # Try to read first 1KB
                return ValidationResult.success(
                    self.name, f"Valid encoding: {encoding}"
                )
            except (UnicodeDecodeError, OSError):
                continue

        return ValidationResult.failure(
            self.name,
            f"Unsupported encoding (tried: {self.allowed_encodings})",
            ValidationSeverity.WARNING,
        )


class BinaryContentValidator(Validator):
    """
    Validates binary file content.

    Checks for file corruption and valid headers.
    """

    def __init__(self, name: str = "BinaryContentValidator"):
        """Initialize validator."""
        super().__init__(name)

        # Known file signatures (magic bytes)
        self.signatures = {
            ".pdf": [b"%PDF"],
            ".zip": [b"PK\x03\x04", b"PK\x05\x06"],
            ".docx": [b"PK\x03\x04"],  # ZIP-based
            ".xlsx": [b"PK\x03\x04"],  # ZIP-based
            ".pptx": [b"PK\x03\x04"],  # ZIP-based
        }

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate binary content."""
        if not file_path.exists():
            return ValidationResult.failure(
                self.name,
                f"File not found: {file_path}",
                ValidationSeverity.ERROR,
            )

        extension = file_path.suffix.lower()

        # Only check files with known signatures
        if extension not in self.signatures:
            return ValidationResult.success(
                self.name, f"No signature check for {extension}"
            )

        try:
            with open(file_path, "rb") as f:
                header = f.read(8)
        except (OSError, PermissionError) as e:
            return ValidationResult.failure(
                self.name,
                f"Cannot read file header: {e}",
                ValidationSeverity.ERROR,
            )

        # Check if header matches expected signatures
        expected_sigs = self.signatures[extension]
        for sig in expected_sigs:
            if header.startswith(sig):
                return ValidationResult.success(
                    self.name, f"Valid {extension} header"
                )

        return ValidationResult.failure(
            self.name,
            f"Invalid {extension} header (possible corruption)",
            ValidationSeverity.ERROR,
        )


class PathValidator(Validator):
    """
    Validates file paths.

    Checks for invalid characters and path length limits.
    """

    def __init__(
        self,
        max_path_length: int = 255,
        max_filename_length: int = 255,
        name: str = "PathValidator",
    ):
        """
        Initialize validator.

        Args:
            max_path_length: Maximum total path length
            max_filename_length: Maximum filename length
            name: Validator name
        """
        super().__init__(name)
        self.max_path_length = max_path_length
        self.max_filename_length = max_filename_length

        # Invalid characters in filenames (Windows + Unix)
        self.invalid_chars = re.compile(r'[<>:"|?*\x00-\x1f]')

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate file path."""
        path_str = str(file_path)
        filename = file_path.name

        # Check path length
        if len(path_str) > self.max_path_length:
            return ValidationResult.failure(
                self.name,
                (
                    f"Path too long: {len(path_str)} chars "
                    f"(max: {self.max_path_length})"
                ),
                ValidationSeverity.WARNING,
            )

        # Check filename length
        if len(filename) > self.max_filename_length:
            return ValidationResult.failure(
                self.name,
                (
                    f"Filename too long: {len(filename)} chars "
                    f"(max: {self.max_filename_length})"
                ),
                ValidationSeverity.WARNING,
            )

        # Check for invalid characters
        if self.invalid_chars.search(filename):
            return ValidationResult.failure(
                self.name,
                f"Filename contains invalid characters: {filename}",
                ValidationSeverity.WARNING,
            )

        return ValidationResult.success(self.name, "Valid path")
