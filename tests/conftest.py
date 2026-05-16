# conftest.py for project-wide pytest fixtures and hooks
# Ensures .env is loaded before any tests run, matching prod entrypoints

import sys
from pathlib import Path

import pytest


@pytest.fixture(scope='session', autouse=True)
def load_dotenv_once():
    """Loads .env from project root before any tests execute."""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path, override=True)
    except ImportError:
        print('[WARN] python-dotenv not installed; .env vars may be missing in tests', file=sys.stderr)
