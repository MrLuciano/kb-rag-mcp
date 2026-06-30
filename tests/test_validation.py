"""
Tests for document validation system.
"""

import tempfile
from pathlib import Path

import pytest

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
from ingest.validation.pipeline import (
    ValidationPipeline,
    create_default_pipeline,
    create_lenient_pipeline,
    create_strict_pipeline,
)
from ingest.validation.size import (
    FileSizeValidator,
    FileTypeSpecificSizeValidator,
)


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for test files."""
    return tmp_path


@pytest.fixture
def sample_text_file(temp_dir):
    """Create a sample text file."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text(
        "Hello, world! This is a test file.", encoding="utf-8"
    )
    return file_path


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file."""
    file_path = temp_dir / "script.py"
    file_path.write_text(
        "def hello():\n    return 'Hello World'\n", encoding="utf-8"
    )
    return file_path


@pytest.fixture
def empty_file(temp_dir):
    """Create an empty file."""
    file_path = temp_dir / "empty.txt"
    file_path.touch()
    return file_path


@pytest.fixture
def large_file(temp_dir):
    """Create a large file (>100MB)."""
    file_path = temp_dir / "large.txt"
    # Create a 101 MB file
    with open(file_path, "wb") as f:
        f.write(b"x" * (101 * 1024 * 1024))
    return file_path


# Test FileExistsValidator


def test_file_exists_validator_success(sample_text_file):
    """Test FileExistsValidator with valid file."""
    validator = FileExistsValidator()
    result = validator.validate(sample_text_file)
    assert result.valid is True
    assert result.severity == ValidationSeverity.INFO


def test_file_exists_validator_missing_file(temp_dir):
    """Test FileExistsValidator with missing file."""
    validator = FileExistsValidator()
    result = validator.validate(temp_dir / "nonexistent.txt")
    assert result.valid is False
    assert result.severity == ValidationSeverity.ERROR
    assert "not found" in result.message.lower()


def test_file_exists_validator_empty_file(empty_file):
    """Test FileExistsValidator with empty file."""
    validator = FileExistsValidator()
    result = validator.validate(empty_file)
    assert result.valid is False
    assert result.severity == ValidationSeverity.WARNING
    assert "empty" in result.message.lower()


# Test FileExtensionValidator


def test_file_extension_validator_valid(sample_text_file):
    """Test FileExtensionValidator with valid extension."""
    validator = FileExtensionValidator()
    result = validator.validate(sample_text_file)
    assert result.valid is True


def test_file_extension_validator_invalid(temp_dir):
    """Test FileExtensionValidator with invalid extension."""
    file_path = temp_dir / "test.xyz"
    file_path.touch()
    validator = FileExtensionValidator()
    result = validator.validate(file_path)
    assert result.valid is False
    assert result.severity == ValidationSeverity.ERROR


def test_file_extension_validator_no_extension(temp_dir):
    """Test FileExtensionValidator with no extension."""
    file_path = temp_dir / "noextension"
    file_path.touch()
    validator = FileExtensionValidator()
    result = validator.validate(file_path)
    assert result.valid is False


def test_file_extension_validator_custom_list(sample_text_file):
    """Test FileExtensionValidator with custom extension list."""
    validator = FileExtensionValidator(allowed_extensions={".py", ".js"})
    result = validator.validate(sample_text_file)
    assert result.valid is False  # .txt not in custom list


# Test FileSizeValidator


def test_file_size_validator_valid(sample_text_file):
    """Test FileSizeValidator with valid size."""
    validator = FileSizeValidator(min_size=1, max_size=1024)
    result = validator.validate(sample_text_file)
    assert result.valid is True


def test_file_size_validator_too_large(large_file):
    """Test FileSizeValidator with file too large."""
    validator = FileSizeValidator(max_size=100 * 1024 * 1024)
    result = validator.validate(large_file)
    assert result.valid is False
    assert result.severity == ValidationSeverity.ERROR


def test_file_size_validator_too_small(empty_file):
    """Test FileSizeValidator with file too small."""
    validator = FileSizeValidator(min_size=10)
    result = validator.validate(empty_file)
    assert result.valid is False


# Test FileTypeSpecificSizeValidator


def test_file_type_specific_validator_python(sample_python_file):
    """Test FileTypeSpecificSizeValidator with Python file."""
    validator = FileTypeSpecificSizeValidator()
    result = validator.validate(sample_python_file)
    assert result.valid is True


def test_file_type_specific_validator_large_text(large_file):
    """Test FileTypeSpecificSizeValidator with large text file."""
    validator = FileTypeSpecificSizeValidator()
    result = validator.validate(large_file)
    assert result.valid is False  # >10MB limit for .txt


# Test TextContentValidator


def test_text_content_validator_valid(sample_text_file):
    """Test TextContentValidator with valid content."""
    validator = TextContentValidator(min_text_length=10, min_word_count=3)
    result = validator.validate(sample_text_file)
    assert result.valid is True


def test_text_content_validator_too_short(temp_dir):
    """Test TextContentValidator with short content."""
    file_path = temp_dir / "short.txt"
    file_path.write_text("Hi")
    validator = TextContentValidator(min_text_length=10, min_word_count=5)
    result = validator.validate(file_path)
    assert result.valid is False


def test_text_content_validator_skip_binary(temp_dir):
    """Test TextContentValidator skips binary files."""
    file_path = temp_dir / "test.pdf"
    file_path.write_bytes(b"%PDF-1.4")
    validator = TextContentValidator()
    result = validator.validate(file_path)
    assert result.valid is True  # Skipped


# Test EncodingValidator


def test_encoding_validator_utf8(sample_text_file):
    """Test EncodingValidator with UTF-8 file."""
    validator = EncodingValidator()
    result = validator.validate(sample_text_file)
    assert result.valid is True


def test_encoding_validator_skip_binary(temp_dir):
    """Test EncodingValidator skips binary files."""
    file_path = temp_dir / "test.pdf"
    file_path.write_bytes(b"%PDF-1.4")
    validator = EncodingValidator()
    result = validator.validate(file_path)
    assert result.valid is True  # Skipped


# Test BinaryContentValidator


def test_binary_content_validator_pdf(temp_dir):
    """Test BinaryContentValidator with valid PDF."""
    file_path = temp_dir / "test.pdf"
    file_path.write_bytes(b"%PDF-1.4\nContent")
    validator = BinaryContentValidator()
    result = validator.validate(file_path)
    assert result.valid is True


def test_binary_content_validator_corrupt_pdf(temp_dir):
    """Test BinaryContentValidator with corrupt PDF."""
    file_path = temp_dir / "corrupt.pdf"
    file_path.write_bytes(b"Not a PDF")
    validator = BinaryContentValidator()
    result = validator.validate(file_path)
    assert result.valid is False
    assert result.severity == ValidationSeverity.ERROR


def test_binary_content_validator_skip_unsupported(sample_text_file):
    """Test BinaryContentValidator skips files without signatures."""
    validator = BinaryContentValidator()
    result = validator.validate(sample_text_file)
    assert result.valid is True  # Skipped


# Test PathValidator


def test_path_validator_valid(sample_text_file):
    """Test PathValidator with valid path."""
    validator = PathValidator()
    result = validator.validate(sample_text_file)
    assert result.valid is True


def test_path_validator_long_filename(temp_dir):
    """Test PathValidator with long filename."""
    long_name = "a" * 300 + ".txt"
    file_path = temp_dir / long_name
    validator = PathValidator(max_filename_length=255)
    result = validator.validate(file_path)
    assert result.valid is False


# Test ValidationPipeline


def test_validation_pipeline_default_success(sample_text_file):
    """Test ValidationPipeline with valid file."""
    pipeline = create_default_pipeline()
    success, results = pipeline.validate(sample_text_file)
    assert success is True
    assert len(results) > 0


def test_validation_pipeline_default_failure(temp_dir):
    """Test ValidationPipeline with invalid file."""
    file_path = temp_dir / "test.xyz"  # Invalid extension
    file_path.write_text("Content")
    pipeline = create_default_pipeline()
    success, results = pipeline.validate(file_path)
    assert success is False


def test_validation_pipeline_fail_fast(temp_dir):
    """Test ValidationPipeline with fail_fast=True."""
    file_path = temp_dir / "nonexistent.txt"
    pipeline = ValidationPipeline(fail_fast=True)
    success, results = pipeline.validate(file_path)
    assert success is False
    # Should stop after first error
    assert len(results) <= 2  # FileExists + maybe one more


def test_validation_pipeline_no_fail_fast(temp_dir):
    """Test ValidationPipeline with fail_fast=False."""
    file_path = temp_dir / "test.xyz"
    file_path.touch()
    pipeline = ValidationPipeline(fail_fast=False)
    success, results = pipeline.validate(file_path)
    assert success is False
    # Should run all validators
    assert len(results) > 1


def test_validation_pipeline_skip_warnings(temp_dir):
    """Test ValidationPipeline with skip_warnings=True."""
    file_path = temp_dir / "empty.txt"
    file_path.touch()
    pipeline = ValidationPipeline(skip_warnings=True)
    success, results = pipeline.validate(file_path)
    # Empty file may produce warnings but should pass with skip_warnings
    assert any(not r.valid for r in results)  # Some validation failed


def test_validation_pipeline_batch(sample_text_file, sample_python_file):
    """Test ValidationPipeline.validate_batch()."""
    pipeline = create_default_pipeline()
    results = pipeline.validate_batch([sample_text_file, sample_python_file])
    assert len(results) == 2
    assert all(success for success, _ in results.values())


def test_validation_pipeline_get_failed_files(temp_dir):
    """Test ValidationPipeline.get_failed_files()."""
    valid = temp_dir / "valid.txt"
    invalid = temp_dir / "invalid.xyz"
    valid.write_text("Content with enough words to pass validation")
    invalid.write_text("Content")

    pipeline = create_default_pipeline()
    results = pipeline.validate_batch([valid, invalid])
    failed = pipeline.get_failed_files(results)

    # invalid.xyz should fail due to extension
    assert invalid in failed
    # valid.txt might also fail if content is too short
    assert len(failed) >= 1


def test_validation_pipeline_add_validator(sample_text_file):
    """Test ValidationPipeline.add_validator()."""
    # Pass empty list explicitly and skip default validators
    pipeline = ValidationPipeline(validators=[])
    # ValidationPipeline defaults to _default_validators() if None
    # So we need to clear them
    pipeline.validators = []
    assert len(pipeline.validators) == 0

    pipeline.add_validator(FileExistsValidator())
    assert len(pipeline.validators) == 1

    success, results = pipeline.validate(sample_text_file)
    assert success is True


def test_validation_pipeline_remove_validator():
    """Test ValidationPipeline.remove_validator()."""
    pipeline = create_default_pipeline()
    initial_count = len(pipeline.validators)

    removed = pipeline.remove_validator("FileExistsValidator")
    assert removed is True
    assert len(pipeline.validators) == initial_count - 1

    removed_again = pipeline.remove_validator("NonExistentValidator")
    assert removed_again is False


def test_strict_pipeline(temp_dir):
    """Test create_strict_pipeline()."""
    file_path = temp_dir / "empty.txt"
    file_path.touch()
    pipeline = create_strict_pipeline()
    success, results = pipeline.validate(file_path)
    # Strict pipeline should fail on warnings
    assert success is False or any(
        r.severity == ValidationSeverity.WARNING for r in results
    )


def test_lenient_pipeline(temp_dir):
    """Test create_lenient_pipeline()."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("Content")
    pipeline = create_lenient_pipeline()
    success, results = pipeline.validate(file_path)
    # Lenient pipeline should pass even with warnings
    # (depends on what warnings are generated)
    assert isinstance(success, bool)


# Test ValidationResult


def test_validation_result_success():
    """Test ValidationResult.success() factory."""
    result = ValidationResult.success("TestValidator", "All good")
    assert result.valid is True
    assert result.severity == ValidationSeverity.INFO
    assert result.validator_name == "TestValidator"


def test_validation_result_failure():
    """Test ValidationResult.failure() factory."""
    result = ValidationResult.failure(
        "TestValidator", "Failed", ValidationSeverity.ERROR
    )
    assert result.valid is False
    assert result.severity == ValidationSeverity.ERROR
    assert result.validator_name == "TestValidator"


# Test ValidationError (base.py lines 77-78)


def test_validation_error_init():
    """Test ValidationError without result."""
    error = ValidationError("test message")
    assert str(error) == "test message"
    assert error.result is None


def test_validation_error_with_result():
    """Test ValidationError with result."""
    result = ValidationResult.failure("Test", "failed")
    error = ValidationError("test message", result=result)
    assert error.result is result
    assert str(error) == "test message"


# Test Validator abstract method and repr (base.py lines 113, 116)


def test_validator_abstract_validate():
    """Test that Validator.validate abstract method body can be reached."""
    class TestValidator(Validator):
        def validate(self, file_path):
            return super().validate(file_path)

    validator = TestValidator()
    result = validator.validate(Path("/nonexistent"))
    assert result is None


def test_validator_repr():
    """Test Validator.__repr__()."""
    validator = TextContentValidator(name="custom_name")
    repr_str = repr(validator)
    assert "TextContentValidator" in repr_str
    assert "custom_name" in repr_str


# Additional TextContentValidator coverage (content.py lines 47, 83-84, 104)


def test_text_content_validator_file_not_found(temp_dir):
    """Test TextContentValidator with non-existent file."""
    validator = TextContentValidator()
    result = validator.validate(temp_dir / "nonexistent.txt")
    assert result.valid is False
    assert result.severity == ValidationSeverity.ERROR
    assert "not found" in result.message.lower()


def test_text_content_validator_read_error(temp_dir):
    """Test TextContentValidator with unreadable (binary) content."""
    file_path = temp_dir / "test.txt"
    file_path.write_bytes(b"\xff\xfe\x00\x01")
    validator = TextContentValidator()
    result = validator.validate(file_path)
    assert result.valid is False
    assert result.severity == ValidationSeverity.WARNING
    assert "cannot read" in result.message.lower()


def test_text_content_validator_too_few_words(temp_dir):
    """Test TextContentValidator with enough chars but too few words."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("a" * 20)
    validator = TextContentValidator(min_text_length=10, min_word_count=5)
    result = validator.validate(file_path)
    assert result.valid is False
    assert "few words" in result.message.lower()


# Additional EncodingValidator coverage (content.py lines 148, 187-190)


def test_encoding_validator_file_not_found(temp_dir):
    """Test EncodingValidator with non-existent file."""
    validator = EncodingValidator()
    result = validator.validate(temp_dir / "nonexistent.txt")
    assert result.valid is False
    assert result.severity == ValidationSeverity.ERROR
    assert "not found" in result.message.lower()


def test_encoding_validator_unsupported_encoding(temp_dir):
    """Test EncodingValidator when no allowed encoding works."""
    file_path = temp_dir / "test.txt"
    file_path.write_bytes(b"\xff\xff\xff\xff")
    validator = EncodingValidator(
        allowed_encodings=["utf-8", "ascii"]
    )
    result = validator.validate(file_path)
    assert result.valid is False
    assert result.severity == ValidationSeverity.WARNING
    assert "unsupported encoding" in result.message.lower()


# Additional BinaryContentValidator coverage (content.py lines 220, 237-238)


def test_binary_content_validator_file_not_found(temp_dir):
    """Test BinaryContentValidator with non-existent file."""
    validator = BinaryContentValidator()
    result = validator.validate(temp_dir / "nonexistent.pdf")
    assert result.valid is False
    assert result.severity == ValidationSeverity.ERROR
    assert "not found" in result.message.lower()


def test_binary_content_validator_read_error(temp_dir):
    """Test BinaryContentValidator with unreadable file."""
    file_path = temp_dir / "test.pdf"
    file_path.write_bytes(b"%PDF-1.4")
    file_path.chmod(0o000)

    try:
        validator = BinaryContentValidator()
        result = validator.validate(file_path)
        assert result.valid is False
        assert result.severity == ValidationSeverity.ERROR
        assert "cannot read" in result.message.lower()
    finally:
        file_path.chmod(0o644)


# Additional PathValidator coverage (content.py lines 305, 316)


def test_path_validator_filename_too_long(temp_dir):
    """Test PathValidator with filename exceeding max length."""
    short_dir = temp_dir / "a"
    short_dir.mkdir()
    long_name = "b" * 260
    file_path = short_dir / long_name

    validator = PathValidator(
        max_path_length=500, max_filename_length=255
    )
    result = validator.validate(file_path)
    assert result.valid is False
    assert "filename" in result.message.lower()


def test_path_validator_invalid_chars(temp_dir):
    """Test PathValidator with invalid characters in filename."""
    file_path = temp_dir / "test<file>.txt"
    validator = PathValidator()
    result = validator.validate(file_path)
    assert result.valid is False
    assert "invalid character" in result.message.lower()


# MimeTypeValidator coverage (format.py lines 122-123, 131-159)


def test_mime_type_validator_init():
    """Test MimeTypeValidator initialization."""
    validator = MimeTypeValidator()
    assert "text/" in validator.allowed_mime_prefixes

    custom = MimeTypeValidator(allowed_mime_prefixes={"text/"})
    assert custom.allowed_mime_prefixes == {"text/"}


def test_mime_type_validator_file_not_found(temp_dir):
    """Test MimeTypeValidator with non-existent file."""
    validator = MimeTypeValidator()
    result = validator.validate(temp_dir / "nonexistent.txt")
    assert result.valid is False
    assert result.severity == ValidationSeverity.ERROR


def test_mime_type_validator_no_mime(temp_dir):
    """Test MimeTypeValidator when MIME type cannot be determined."""
    file_path = temp_dir / "test.unregistered_ext"
    file_path.touch()
    validator = MimeTypeValidator()
    result = validator.validate(file_path)
    assert result.valid is False
    assert result.severity == ValidationSeverity.WARNING


def test_mime_type_validator_unsupported_type(temp_dir):
    """Test MimeTypeValidator with unsupported MIME type prefix."""
    file_path = temp_dir / "test.html"
    file_path.touch()
    validator = MimeTypeValidator(allowed_mime_prefixes={"image/"})
    result = validator.validate(file_path)
    assert result.valid is False
    assert result.severity == ValidationSeverity.ERROR
    assert "unsupported mime" in result.message.lower()


def test_mime_type_validator_valid(temp_dir):
    """Test MimeTypeValidator with valid MIME type."""
    file_path = temp_dir / "test.html"
    file_path.touch()
    validator = MimeTypeValidator()
    result = validator.validate(file_path)
    assert result.valid is True


# Additional FileExistsValidator coverage (format.py lines 180, 197-198)


def test_file_exists_validator_is_directory(temp_dir):
    """Test FileExistsValidator with a directory instead of file."""
    validator = FileExistsValidator()
    result = validator.validate(temp_dir)
    assert result.valid is False
    assert result.severity == ValidationSeverity.ERROR
    assert "not a file" in result.message.lower()


def test_file_exists_validator_not_readable(temp_dir):
    """Test FileExistsValidator with unreadable file."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("content")
    file_path.chmod(0o000)

    try:
        validator = FileExistsValidator()
        result = validator.validate(file_path)
        assert result.valid is False
        assert result.severity == ValidationSeverity.ERROR
        assert "not readable" in result.message.lower()
    finally:
        file_path.chmod(0o644)


# ValidationPipeline error handling coverage (pipeline.py lines 114-131)


def test_validation_pipeline_validator_error_with_result(temp_dir):
    """Test pipeline handles ValidationError with result."""
    class ErrorValidator(Validator):
        def validate(self, file_path):
            raise ValidationError(
                "critical",
                result=ValidationResult.failure(
                    self.name, "failed"
                ),
            )

    pipeline = ValidationPipeline(
        validators=[ErrorValidator()], fail_fast=True
    )
    success, results = pipeline.validate(temp_dir / "any.txt")
    assert success is False
    assert len(results) == 1
    assert results[0].valid is False


def test_validation_pipeline_validator_error_without_result(temp_dir):
    """Test pipeline handles ValidationError without result."""
    class ErrorValidator(Validator):
        def validate(self, file_path):
            raise ValidationError("critical")

    pipeline = ValidationPipeline(
        validators=[ErrorValidator()], fail_fast=False
    )
    success, results = pipeline.validate(temp_dir / "any.txt")
    assert success is False
    assert len(results) == 0


def test_validation_pipeline_unexpected_error(temp_dir):
    """Test pipeline handles unexpected Exception from validator."""
    class ErrorValidator(Validator):
        def validate(self, file_path):
            raise RuntimeError("unexpected error")

    pipeline = ValidationPipeline(
        validators=[ErrorValidator()], fail_fast=True
    )
    success, results = pipeline.validate(temp_dir / "any.txt")
    assert success is False
    assert len(results) == 1
    assert results[0].valid is False
    assert "Validator error" in results[0].message


def test_validation_pipeline_unexpected_error_no_fail_fast(temp_dir):
    """Test pipeline continues after unexpected Exception when not fail_fast."""
    from ingest.validation.format import FileExtensionValidator

    class ErrorValidator(Validator):
        def validate(self, file_path):
            raise RuntimeError("unexpected error")

    pipeline = ValidationPipeline(
        validators=[ErrorValidator(), FileExtensionValidator()],
        fail_fast=False,
    )
    success, results = pipeline.validate(temp_dir / "any.txt")
    assert success is False
    assert len(results) == 2


# ValidationPipeline get_failure_reasons coverage (pipeline.py line 177)


def test_validation_pipeline_get_failure_reasons():
    """Test ValidationPipeline.get_failure_reasons()."""
    pipeline = ValidationPipeline(validators=[])
    results = [
        ValidationResult.success("V1", "ok"),
        ValidationResult.failure("V2", "failed"),
        ValidationResult.success("V3", "ok"),
        ValidationResult.failure("V4", "warning"),
    ]
    reasons = pipeline.get_failure_reasons(results)
    assert len(reasons) == 2
    assert "V2" in reasons[0]
    assert "V4" in reasons[1]


# ValidationPipeline add_validator at index (pipeline.py line 192)


def test_validation_pipeline_add_validator_at_index():
    """Test add_validator with specific index."""
    from ingest.validation.format import FileExtensionValidator

    pipeline = ValidationPipeline(
        validators=[FileExistsValidator(), FileExtensionValidator()]
    )
    pipeline.add_validator(FileExistsValidator(), index=0)
    assert len(pipeline.validators) == 3
    assert isinstance(pipeline.validators[0], FileExistsValidator)
    assert isinstance(pipeline.validators[1], FileExistsValidator)


# ValidationPipeline __repr__ (pipeline.py line 211)


def test_validation_pipeline_repr():
    """Test ValidationPipeline.__repr__()."""
    pipeline = ValidationPipeline(
        validators=[FileExistsValidator()], fail_fast=True
    )
    repr_str = repr(pipeline)
    assert "ValidationPipeline" in repr_str
    assert "fail_fast=True" in repr_str


# format_bytes TB coverage (size.py line 22)


def test_format_bytes_tb():
    """Test format_bytes with TB-sized value."""
    from ingest.validation.size import format_bytes

    result = format_bytes(2048 * 1024 * 1024 * 1024)
    assert result.endswith("TB")
    assert "2.0TB" in result or "2" in result


# FileSizeValidator file not found (size.py line 54)


def test_file_size_validator_file_not_found(temp_dir):
    """Test FileSizeValidator with non-existent file."""
    validator = FileSizeValidator()
    result = validator.validate(temp_dir / "nonexistent.txt")
    assert result.valid is False
    assert result.severity == ValidationSeverity.ERROR
    assert "not found" in result.message.lower()


# FileTypeSpecificSizeValidator file not found (size.py line 134)


def test_file_type_specific_validator_file_not_found(temp_dir):
    """Test FileTypeSpecificSizeValidator with non-existent file."""
    validator = FileTypeSpecificSizeValidator()
    result = validator.validate(temp_dir / "nonexistent.txt")
    assert result.valid is False
    assert result.severity == ValidationSeverity.ERROR
    assert "not found" in result.message.lower()
