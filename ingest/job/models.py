"""
Job models and enums for the ingestion pipeline.

Defines the data structures for jobs, job status, and job priorities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    """Job lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobPriority(int, Enum):
    """Job priority levels (higher number = higher priority)."""

    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200


@dataclass
class Job:
    """
    Represents an ingestion job.

    Attributes:
        job_id: Unique identifier (UUID)
        status: Current job status
        priority: Job priority level
        docs_path: Path to documents directory
        product_override: Optional product name override
        workers: Number of parallel workers
        clean: Whether to clean KB before ingesting
        force: Whether to force re-ingestion
        sync: Whether to sync deleted files
        created_at: Job creation timestamp
        started_at: Job start timestamp
        completed_at: Job completion timestamp
        error: Error message if failed
        total_files: Total files to process
        processed_files: Files processed so far
        total_chunks: Total chunks generated
    """

    job_id: str
    status: JobStatus
    priority: JobPriority
    docs_path: str
    product_override: Optional[str] = None
    workers: int = 2
    clean: bool = False
    force: bool = False
    sync: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    total_files: int = 0
    processed_files: int = 0
    total_chunks: int = 0

    def is_terminal(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        )

    def is_active(self) -> bool:
        """Check if job is currently active."""
        return self.status in (JobStatus.PENDING, JobStatus.RUNNING)

    def can_pause(self) -> bool:
        """Check if job can be paused."""
        return self.status in (JobStatus.PENDING, JobStatus.RUNNING)

    def can_resume(self) -> bool:
        """Check if job can be resumed."""
        return self.status == JobStatus.PAUSED

    def can_cancel(self) -> bool:
        """Check if job can be cancelled."""
        return self.status in (
            JobStatus.PENDING,
            JobStatus.RUNNING,
            JobStatus.PAUSED,
        )


@dataclass
class JobProgress:
    """
    Tracks progress for a specific file within a job.

    Attributes:
        job_id: Associated job ID
        file_path: Relative path to file
        status: Processing status
        chunks_generated: Number of chunks created
        error: Error message if failed
        started_at: Processing start time
        completed_at: Processing completion time
    """

    job_id: str
    file_path: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    chunks_generated: int = 0
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
