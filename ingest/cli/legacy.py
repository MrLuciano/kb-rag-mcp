"""
Legacy CLI wrapper with deprecation warnings.

This wrapper maintains backward compatibility with the old argparse-based
CLI (ingest/ingest.py) while warning users to migrate to the new kb-rag
CLI.
"""

import sys
from pathlib import Path

# Load .env before imports
_project_root = Path(__file__).parent.parent.parent
from config.bootstrap_env import bootstrap_env
bootstrap_env()

# Add server/ to path
sys.path.insert(0, str(_project_root / "server"))


def show_deprecation_warning() -> None:
    """Show deprecation warning for legacy CLI."""
    msg = """
╔════════════════════════════════════════════════════════════════╗
║                     DEPRECATION WARNING                        ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  The legacy 'ingest.py' CLI is deprecated and will be         ║
║  removed in a future version.                                 ║
║                                                                ║
║  Please migrate to the new 'kb-rag' CLI:                      ║
║                                                                ║
║    OLD: python ingest.py --docs /path --workers 4             ║
║    NEW: kb-rag job create --docs /path --workers 4            ║
║                                                                ║
║  New features:                                                 ║
║    • Job queue with priority scheduling                       ║
║    • Real-time progress monitoring                            ║
║    • Pause/resume/cancel jobs                                 ║
║    • Better error handling                                    ║
║                                                                ║
║  Run 'kb-rag --help' to learn more.                           ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
"""
    print(msg, file=sys.stderr)
    print()  # Extra newline for readability


def main() -> None:
    """
    Legacy CLI entry point.

    This wrapper:
    1. Shows deprecation warning
    2. Delegates to the original ingest.py main()
    """
    show_deprecation_warning()

    # Import and run legacy ingest
    try:
        # Import the legacy module
        # Note: We import 'ingest.ingest' not just 'ingest'
        # because we're in the ingest package
        import ingest.ingest as legacy_ingest

        # Call the main function
        legacy_ingest.main()

    except ImportError as e:
        print(
            f"Error: Could not import legacy ingest module: {e}",
            file=sys.stderr,
        )
        print(
            "\nPlease ensure ingest/ingest.py exists and is valid.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error running legacy CLI: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
