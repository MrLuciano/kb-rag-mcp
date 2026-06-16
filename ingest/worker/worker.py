"""
Worker for processing individual files with rate limiting.

Wraps the file processing logic with error handling, retry,
and progress reporting.
"""

import logging
from pathlib import Path
from typing import Optional

from ingest.validation.pipeline import (
    ValidationPipeline,
    create_default_pipeline,
)
from ingest.worker.limiter import RateLimiter

log = logging.getLogger("kb-ingest.worker.worker")


class WorkerResult:
    """
    Result of processing a single file.

    Attributes:
        file_path: Path to processed file
        success: Whether processing succeeded
        chunks_generated: Number of chunks created
        error: Error message if failed
        status: Processing status (ok/skipped/error/validation_failed)
        retries: Number of retry attempts
        validation_errors: List of validation error messages
    """

    def __init__(
        self,
        file_path: Path,
        success: bool,
        chunks_generated: int = 0,
        error: Optional[str] = None,
        status: str = "ok",
        retries: int = 0,
        validation_errors: Optional[list[str]] = None,
    ):
        self.file_path = file_path
        self.success = success
        self.chunks_generated = chunks_generated
        self.error = error
        self.status = status
        self.retries = retries
        self.validation_errors = validation_errors or []


class FileWorker:
    """
    Worker for processing individual files.

    Handles file processing with rate limiting, error handling,
    and retry logic.
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        max_retries: int = 3,
        validation_pipeline: Optional[ValidationPipeline] = None,
        skip_validation: bool = False,
    ):
        """
        Initialize worker.

        Args:
            rate_limiter: Rate limiter for API calls
            max_retries: Maximum retry attempts on failure
            validation_pipeline: Optional validation pipeline.
                                Defaults to create_default_pipeline().
            skip_validation: Skip validation (for testing or legacy mode)
        """
        self.rate_limiter = rate_limiter
        self.max_retries = max_retries
        self.validation_pipeline = (
            validation_pipeline
            if validation_pipeline is not None
            else create_default_pipeline()
        )
        self.skip_validation = skip_validation

    async def process_file(
        self,
        file_path: Path,
        docs_root: Path,
        store,
        registry,
        product_override: Optional[str] = None,
        force: bool = False,
    ) -> WorkerResult:
        """
        Process a single file with rate limiting and retries.

        Args:
            file_path: Path to file
            docs_root: Root directory for relative paths
            store: Vector store instance
            registry: File registry
            product_override: Optional product name
            force: Force re-ingestion

        Returns:
            WorkerResult with processing outcome
        """
        # Validate file before processing
        if not self.skip_validation:
            is_valid, validation_results = self.validation_pipeline.validate(
                file_path
            )

            if not is_valid:
                # Get failure reasons
                failure_reasons = self.validation_pipeline.get_failure_reasons(
                    validation_results
                )
                log.warning(
                    f"Validation failed for {file_path.name}: "
                    f"{'; '.join(failure_reasons)}"
                )
                return WorkerResult(
                    file_path=file_path,
                    success=False,
                    status="validation_failed",
                    error="Validation failed",
                    validation_errors=failure_reasons,
                )

        retries = 0

        while retries <= self.max_retries:
            try:
                # Acquire rate limit token before processing
                if self.rate_limiter:
                    await self.rate_limiter.acquire()

                # Import processing function
                from ingest.ingest import process_file as ingest_process

                # Process the file
                chunks, status = await ingest_process(
                    file_path=file_path,
                    docs_root=docs_root,
                    store=store,
                    registry=registry,
                    product_override=product_override,
                    force=force,
                )

                # Return success result
                return WorkerResult(
                    file_path=file_path,
                    success=True,
                    chunks_generated=chunks,
                    status=status,
                    retries=retries,
                )

            except Exception as e:
                retries += 1
                error_msg = str(e)

                if retries > self.max_retries:
                    log.error(
                        f"Failed to process {file_path.name} "
                        f"after {retries} attempts: {error_msg}"
                    )
                    return WorkerResult(
                        file_path=file_path,
                        success=False,
                        error=error_msg,
                        status="error",
                        retries=retries,
                    )

                log.warning(
                    f"Retry {retries}/{self.max_retries} "
                    f"for {file_path.name}: {error_msg}"
                )

        # Should not reach here
        return WorkerResult(
            file_path=file_path,
            success=False,
            error="Max retries exceeded",
            status="error",
            retries=retries,
        )


class WorkerStats:
    """
    Statistics for worker activity.

    Tracks files processed, errors, retries, and throughput.
    """

    def __init__(self):
        self.files_processed = 0
        self.files_skipped = 0
        self.files_failed = 0
        self.files_validation_failed = 0
        self.chunks_generated = 0
        self.total_retries = 0

    def record_result(self, result: WorkerResult) -> None:
        """Record a worker result in stats."""
        if result.status == "skipped":
            self.files_skipped += 1
        elif result.status == "validation_failed":
            self.files_validation_failed += 1
        elif result.success:
            self.files_processed += 1
            self.chunks_generated += result.chunks_generated
        else:
            self.files_failed += 1

        self.total_retries += result.retries

    def summary(self) -> dict:
        """Get statistics summary."""
        return {
            "processed": self.files_processed,
            "skipped": self.files_skipped,
            "failed": self.files_failed,
            "validation_failed": self.files_validation_failed,
            "chunks": self.chunks_generated,
            "retries": self.total_retries,
            "total": (
                self.files_processed
                + self.files_skipped
                + self.files_failed
                + self.files_validation_failed
            ),
        }

    def __str__(self) -> str:
        """String representation of stats."""
        s = self.summary()
        return (
            f"Processed: {s['processed']}, "
            f"Skipped: {s['skipped']}, "
            f"Failed: {s['failed']}, "
            f"Validation Failed: {s['validation_failed']}, "
            f"Chunks: {s['chunks']}, "
            f"Retries: {s['retries']}"
        )
