"""
Validation pipeline orchestrator.

Coordinates multiple validators and aggregates results.
"""

from pathlib import Path
from typing import Optional

from ingest.validation.base import (
    ValidationError,
    ValidationResult,
    ValidationSeverity,
    Validator,
)
from ingest.validation.content import (
    BinaryContentValidator,
    EncodingValidator,
    PathValidator,
    TextContentValidator,
)
from ingest.validation.format import (
    FileExistsValidator,
    FileExtensionValidator,
    MimeTypeValidator,
)
from ingest.validation.size import (
    FileSizeValidator,
    FileTypeSpecificSizeValidator,
)


class ValidationPipeline:
    """
    Orchestrates multiple validators in sequence.

    Runs validators in order and aggregates results. Can be configured
    to fail-fast (stop on first error) or collect all results.
    """

    def __init__(
        self,
        validators: Optional[list[Validator]] = None,
        fail_fast: bool = True,
        skip_warnings: bool = False,
    ):
        """
        Initialize validation pipeline.

        Args:
            validators: List of validators to run. If None, uses
                       default validators.
            fail_fast: Stop on first ERROR severity result
            skip_warnings: Treat WARNING results as success
        """
        self.validators = (
            validators
            if validators is not None
            else self._default_validators()
        )
        self.fail_fast = fail_fast
        self.skip_warnings = skip_warnings

    @staticmethod
    def _default_validators() -> list[Validator]:
        """Create default validator set."""
        return [
            # Basic checks first
            FileExistsValidator(),
            PathValidator(),
            # Format validation
            FileExtensionValidator(),
            # Size validation (type-specific is more permissive)
            FileTypeSpecificSizeValidator(),
            # Content validation
            EncodingValidator(),
            BinaryContentValidator(),
            TextContentValidator(),
        ]

    def validate(
        self, file_path: Path
    ) -> tuple[bool, list[ValidationResult]]:
        """
        Run all validators on a file.

        Args:
            file_path: Path to file to validate

        Returns:
            Tuple of (success: bool, results: list[ValidationResult])
            success is True if all validators passed (or only warnings
            if skip_warnings=True)

        Raises:
            ValidationError: If a critical validation error occurs
        """
        results: list[ValidationResult] = []
        overall_success = True

        for validator in self.validators:
            try:
                result = validator.validate(file_path)
                results.append(result)

                # Check if we should fail
                if not result.valid:
                    if result.severity == ValidationSeverity.ERROR:
                        overall_success = False
                        if self.fail_fast:
                            break
                    elif (
                        result.severity == ValidationSeverity.WARNING
                        and not self.skip_warnings
                    ):
                        overall_success = False

            except ValidationError as e:
                # Critical error from validator
                if e.result:
                    results.append(e.result)
                overall_success = False
                if self.fail_fast:
                    break
            except Exception as e:
                # Unexpected error
                result = ValidationResult.failure(
                    validator.name,
                    f"Validator error: {e}",
                    ValidationSeverity.ERROR,
                )
                results.append(result)
                overall_success = False
                if self.fail_fast:
                    break

        return overall_success, results

    def validate_batch(
        self, file_paths: list[Path]
    ) -> dict[Path, tuple[bool, list[ValidationResult]]]:
        """
        Validate multiple files.

        Args:
            file_paths: List of file paths to validate

        Returns:
            Dict mapping file paths to (success, results) tuples
        """
        return {
            path: self.validate(path) for path in file_paths
        }

    def get_failed_files(
        self, batch_results: dict[Path, tuple[bool, list[ValidationResult]]]
    ) -> list[Path]:
        """
        Get list of files that failed validation.

        Args:
            batch_results: Results from validate_batch()

        Returns:
            List of file paths that failed validation
        """
        return [
            path
            for path, (success, _) in batch_results.items()
            if not success
        ]

    def get_failure_reasons(
        self, results: list[ValidationResult]
    ) -> list[str]:
        """
        Extract failure reasons from validation results.

        Args:
            results: List of validation results

        Returns:
            List of failure messages (only failed validations)
        """
        return [
            f"{r.validator_name}: {r.message}"
            for r in results
            if not r.valid
        ]

    def add_validator(self, validator: Validator, index: Optional[int] = None):
        """
        Add a validator to the pipeline.

        Args:
            validator: Validator to add
            index: Position to insert validator. If None, appends to end.
        """
        if index is None:
            self.validators.append(validator)
        else:
            self.validators.insert(index, validator)

    def remove_validator(self, name: str) -> bool:
        """
        Remove a validator by name.

        Args:
            name: Name of validator to remove

        Returns:
            True if validator was found and removed
        """
        for i, validator in enumerate(self.validators):
            if validator.name == name:
                self.validators.pop(i)
                return True
        return False

    def __repr__(self) -> str:
        return (
            f"ValidationPipeline(validators={len(self.validators)}, "
            f"fail_fast={self.fail_fast})"
        )


def create_default_pipeline(
    fail_fast: bool = True, skip_warnings: bool = False
) -> ValidationPipeline:
    """
    Create a validation pipeline with sensible defaults.

    Args:
        fail_fast: Stop on first error
        skip_warnings: Treat warnings as success

    Returns:
        Configured ValidationPipeline
    """
    return ValidationPipeline(
        fail_fast=fail_fast, skip_warnings=skip_warnings
    )


def create_strict_pipeline() -> ValidationPipeline:
    """
    Create a strict validation pipeline.

    All validators, fail-fast on errors, warnings count as failures.
    """
    return ValidationPipeline(fail_fast=True, skip_warnings=False)


def create_lenient_pipeline() -> ValidationPipeline:
    """
    Create a lenient validation pipeline.

    All validators, no fail-fast, warnings are ignored.
    """
    return ValidationPipeline(fail_fast=False, skip_warnings=True)
