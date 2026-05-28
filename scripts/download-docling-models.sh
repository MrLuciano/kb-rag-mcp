#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Pre-download all docling AI models into a persistent cache
# so batch PDF extraction never hits HuggingFace at runtime.
#
# Usage:
#   ./scripts/download-docling-models.sh
#
# After running, set DOCLING_ARTIFACTS_PATH to the chosen
# directory (printed at the end) and docling will run fully
# offline with zero network calls.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

MODELS_DIR="${1:-models/docling}"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "=== kb-rag-mcp: Pre-download docling models ==="
echo ""
echo "  Target: $MODELS_DIR"
echo ""

mkdir -p "$MODELS_DIR"
export DOCLING_ARTIFACTS_PATH="$PWD/$MODELS_DIR"

# ── Download models by running a single conversion ────────
# Docling lazily downloads: layout model, table model, ocr models.
# We use a tiny valid PDF (the 1-page cert fixture) to trigger all.
FIXTURE="qa/fixtures/XECMFNDv16_OpenText Extended ECM for SAP Solutions Foundation v16 Certificate.pdf"
if [ ! -f "$FIXTURE" ]; then
    echo "  WARNING: fixture PDF not found at $FIXTURE"
    echo "  Run from project root with QA fixtures in place."
    exit 1
fi

python3 -c "
import os
os.environ['DOCLING_ARTIFACTS_PATH'] = '$PWD/$MODELS_DIR'
from ingest.docling_utils import get_docling_converter
conv = get_docling_converter()
conv.convert('$FIXTURE')
print('  Models downloaded and cached successfully.')
"

echo ""
echo "  ✓ All docling models cached in: $MODELS_DIR"
echo ""
echo "  To use offline, set DOCLING_ARTIFACTS_PATH before running ingestion:"
echo ""
echo "    export DOCLING_ARTIFACTS_PATH=$PWD/$MODELS_DIR"
echo ""
echo "  Or add it to your .env file:"
echo "    DOCLING_ARTIFACTS_PATH=$PWD/$MODELS_DIR"
echo ""
