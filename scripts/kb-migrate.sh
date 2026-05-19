#!/usr/bin/env bash
# KB-RAG Migration Tool
# Usage:
#   ./scripts/kb-migrate.sh export --output /tmp/kb-backup.tar.gz
#   ./scripts/kb-migrate.sh import --package /tmp/kb-backup.tar.gz --target-dir /opt/kb-rag/data
#   ./scripts/kb-migrate.sh validate --package /tmp/kb-backup.tar.gz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

SUBCOMMAND="${1:-help}"
shift || true

case "$SUBCOMMAND" in
    export)
        PYTHONPATH=. $PYTHON -m scripts.migrate.export "$@"
        ;;
    import)
        PYTHONPATH=. $PYTHON -m scripts.migrate.import_ "$@"
        ;;
    validate)
        PYTHONPATH=. $PYTHON -m scripts.migrate.validate "$@"
        ;;
    help|--help|-h)
        echo "KB-RAG Migration Tool"
        echo ""
        echo "Usage:"
        echo "  $0 export   --output <path.tar.gz> [--qdrant-url URL] [--collection NAME]"
        echo "  $0 import   --package <path.tar.gz> --target-dir <dir> [--skip-qdrant]"
        echo "  $0 validate --package <path.tar.gz>"
        echo ""
        echo "Environment variables:"
        echo "  QDRANT_URL        Qdrant base URL (default: http://localhost:6333)"
        echo "  QDRANT_COLLECTION Collection name (default: kb_docs)"
        ;;
    *)
        echo "[ERROR] Unknown subcommand: $SUBCOMMAND"
        echo "Run '$0 help' for usage."
        exit 1
        ;;
esac
