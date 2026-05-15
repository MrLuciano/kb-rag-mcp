"""
Structured logging configuration for KB ingestion system.

Provides JSON logging format, per-module log levels,
and context injection for job_id, worker_id, etc.
"""

import logging
import sys
from typing import Any, Dict, Optional

try:
    import datetime
    import json
except ImportError:
    json = None  # type: ignore
    datetime = None  # type: ignore


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs in JSON format with standard fields:
    - timestamp: ISO 8601 timestamp
    - level: Log level (INFO, ERROR, etc.)
    - logger: Logger name
    - message: Log message
    - context: Additional context (job_id, worker_id, etc.)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.datetime.fromtimestamp(
                record.created
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom context from record
        if hasattr(record, "context"):
            log_data["context"] = record.context

        # Add common fields if present
        for field in ["job_id", "worker_id", "file_path"]:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        return json.dumps(log_data)


class ContextLogger(logging.LoggerAdapter):
    """
    Logger adapter that injects context into log records.

    Usage:
        logger = ContextLogger(
            logging.getLogger(__name__),
            {"job_id": "abc123"}
        )
        logger.info("Processing file")
        # Output: {..., "job_id": "abc123", ...}
    """

    def process(
        self, msg: str, kwargs: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """Inject context into log record."""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Default log level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON formatter (True) or plain text (False)
        log_file: Optional file path for file logging
    """
    # Remove existing handlers
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # Create handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if json_format:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    handlers.append(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        if json_format:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] " "%(name)s: %(message)s"
                )
            )
        handlers.append(file_handler)

    # Configure root logger
    root.setLevel(getattr(logging, level.upper()))
    for handler in handlers:
        root.addHandler(handler)


def set_module_level(module: str, level: str) -> None:
    """
    Set log level for specific module.

    Args:
        module: Module name (e.g., "kb-ingest.worker")
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    logger = logging.getLogger(module)
    logger.setLevel(getattr(logging, level.upper()))


def get_logger(
    name: str, context: Optional[Dict[str, Any]] = None
) -> logging.Logger | ContextLogger:
    """
    Get logger with optional context.

    Args:
        name: Logger name
        context: Optional context dict

    Returns:
        Logger or ContextLogger with context
    """
    logger = logging.getLogger(name)
    if context:
        return ContextLogger(logger, context)
    return logger


# Module-level log configuration
DEFAULT_LEVELS = {
    "kb-ingest": "INFO",
    "kb-ingest.worker": "INFO",
    "kb-ingest.job": "INFO",
    "kb-ingest.ingest": "INFO",
    "kb-ingest.registry": "INFO",
    "kb-ingest.observability": "INFO",
}


def configure_default_levels() -> None:
    """Configure default log levels for all modules."""
    for module, level in DEFAULT_LEVELS.items():
        set_module_level(module, level)
