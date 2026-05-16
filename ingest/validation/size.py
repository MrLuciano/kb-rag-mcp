"""
File size validators.

Validates file sizes against min/max thresholds.
"""

from pathlib import Path

from ingest.validation.base import (
    ValidationResult,
    ValidationSeverity,
    Validator,
)


def format_bytes(bytes_val: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f}TB"


class FileSizeValidator(Validator):
    """
    Validates file size is within acceptable range.

    Rejects files that are too small (empty/corrupt) or too large
    (may cause memory issues or timeouts).
    """

    def __init__(
        self,
        min_size: int = 1,  # 1 byte minimum
        max_size: int = 100 * 1024 * 1024,  # 100 MB default
        name: str = "FileSizeValidator",
    ):
        """
        Initialize validator.

        Args:
            min_size: Minimum file size in bytes (default: 1)
            max_size: Maximum file size in bytes (default: 100 MB)
            name: Validator name
        """
        super().__init__(name)
        self.min_size = min_size
        self.max_size = max_size

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate file size."""
        if not file_path.exists():
            return ValidationResult.failure(
                self.name,
                f"File not found: {file_path}",
                ValidationSeverity.ERROR,
            )

        file_size = file_path.stat().st_size

        if file_size < self.min_size:
            return ValidationResult.failure(
                self.name,
                (
                    f"File too small: {format_bytes(file_size)} "
                    f"(min: {format_bytes(self.min_size)})"
                ),
                ValidationSeverity.WARNING,
            )

        if file_size > self.max_size:
            return ValidationResult.failure(
                self.name,
                (
                    f"File too large: {format_bytes(file_size)} "
                    f"(max: {format_bytes(self.max_size)})"
                ),
                ValidationSeverity.ERROR,
            )

        return ValidationResult.success(
            self.name, f"Valid size: {format_bytes(file_size)}"
        )


class FileTypeSpecificSizeValidator(Validator):
    """
    Validates file size based on file type.

    Different file types have different reasonable size limits.
    """

    def __init__(self, name: str = "FileTypeSpecificSizeValidator"):
        """Initialize validator with type-specific limits."""
        super().__init__(name)

        # Type-specific size limits (in bytes)
        self.size_limits = {
            # Text files: 10 MB
            ".txt": 10 * 1024 * 1024,
            ".md": 10 * 1024 * 1024,
            ".rst": 10 * 1024 * 1024,
            # Code files: 5 MB
            ".py": 5 * 1024 * 1024,
            ".js": 5 * 1024 * 1024,
            ".ts": 5 * 1024 * 1024,
            ".java": 5 * 1024 * 1024,
            ".go": 5 * 1024 * 1024,
            ".rs": 5 * 1024 * 1024,
            ".cpp": 5 * 1024 * 1024,
            ".c": 5 * 1024 * 1024,
            ".cs": 5 * 1024 * 1024,
            # Config files: 1 MB
            ".json": 1 * 1024 * 1024,
            ".yaml": 1 * 1024 * 1024,
            ".yml": 1 * 1024 * 1024,
            ".xml": 1 * 1024 * 1024,
            # Documents: 50 MB
            ".pdf": 50 * 1024 * 1024,
            ".docx": 50 * 1024 * 1024,
            ".doc": 50 * 1024 * 1024,
            # Spreadsheets: 20 MB
            ".xlsx": 20 * 1024 * 1024,
            ".xls": 20 * 1024 * 1024,
            # Presentations: 100 MB
            ".pptx": 100 * 1024 * 1024,
            ".ppt": 100 * 1024 * 1024,
        }

    def validate(self, file_path: Path) -> ValidationResult:
        """Validate file size based on type."""
        if not file_path.exists():
            return ValidationResult.failure(
                self.name,
                f"File not found: {file_path}",
                ValidationSeverity.ERROR,
            )

        extension = file_path.suffix.lower()
        file_size = file_path.stat().st_size

        # Get type-specific limit or use default 100 MB
        max_size = self.size_limits.get(extension, 100 * 1024 * 1024)

        if file_size > max_size:
            return ValidationResult.failure(
                self.name,
                (
                    f"File too large for type {extension}: "
                    f"{format_bytes(file_size)} "
                    f"(max: {format_bytes(max_size)})"
                ),
                ValidationSeverity.ERROR,
            )

        return ValidationResult.success(
            self.name,
            f"Valid size for {extension}: {format_bytes(file_size)}",
        )
