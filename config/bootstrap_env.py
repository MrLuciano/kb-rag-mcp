"""
Single canonical environment loader for kb-rag-mcp.

All entry points call bootstrap_env() instead of copy-pasting load_dotenv blocks.
This is the only place in the codebase that calls load_dotenv directly.
"""

import logging
import os
from pathlib import Path

log = logging.getLogger("kb-mcp.config")


def bootstrap_env(env_file: str | None = None) -> None:
    """
    Load environment variables from .env file.

    Resolves the .env path in this order:
    1. Explicit ``env_file`` argument (if provided)
    2. ``KB_ENV_FILE`` environment variable
    3. ``.env`` in the project root (parent of the ``config/`` directory)

    Safe to call multiple times — python-dotenv does not override existing
    environment variables unless ``override=True`` is explicitly requested.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        log.debug("python-dotenv not installed; skipping .env load")
        return

    if env_file is None:
        env_file = os.environ.get("KB_ENV_FILE")

    if env_file is None:
        # Default: .env at project root (two levels up from config/)
        env_file = str(Path(__file__).parent.parent / ".env")

    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path, override=True)
        log.debug(f"Loaded env from {env_path}")
    else:
        log.debug(f"No .env file found at {env_path}; skipping")

    # Seed config table from environment after dotenv loads
    try:
        from kb_server.config import config

        config.load_from_env()
    except Exception:
        log.debug("ConfigLoader seeding skipped (bootstrap timing)")
