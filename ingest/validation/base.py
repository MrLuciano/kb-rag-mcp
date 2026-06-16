"""
Base validator classes and types.

Defines the abstract Validator interface and validation result types.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class ValidationSeverity(str, Enum):
    """Severity levels for validation results."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    """
    Result of a validation check.

    Attributes:
        valid: Whether the validation passed
        severity: Severity level if validation failed
        message: Human-readable validation message
        validator_name: Name of the validator that produced this result
    """

    valid: bool
    severity: ValidationSeverity
    message: str
    validator_name: str

    @classmethod
    def success(
        cls, validator_name: str, message: str = "Valid"
    ) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(
            valid=True,
            severity=ValidationSeverity.INFO,
            message=message,
            validator_name=validator_name,
        )

    @classmethod
    def failure(
        cls,
        validator_name: str,
        message: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
    ) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(
            valid=False,
            severity=severity,
            message=message,
            validator_name=validator_name,
        )


class ValidationError(Exception):
    """
    Exception raised when validation fails critically.

    Contains the validation result that triggered the error.
    """

    def __init__(
        self, message: str, result: Optional[ValidationResult] = None
    ):
        super().__init__(message)
        self.result = result


class Validator(ABC):
    """
    Abstract base class for document validators.

    Validators check specific aspects of documents (format, size, content)
    and return ValidationResult objects.
    """

    def __init__(self, name: Optional[str] = None):
        """
        Initialize validator.

        Args:
            name: Optional custom name for this validator.
                  Defaults to class name.
        """
        self.name = name or self.__class__.__name__

    @abstractmethod
    def validate(self, file_path: Path) -> ValidationResult:
        """
        Validate a document file.

        Args:
            file_path: Path to the file to validate

        Returns:
            ValidationResult indicating success or failure

        Raises:
            ValidationError: For critical validation failures
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
