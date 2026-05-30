#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Pre-download all docling AI models into a persistent cache
# so batch PDF extraction never hits HuggingFace at runtime.
#
# Usage:
#   ./scripts/download-docling-models.sh [TARGET_DIR]
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

# ── Download each model component explicitly ──────────────
# Docling does not auto-download when DOCLING_ARTIFACTS_PATH
# is set — it expects the artifacts to already exist. We must
# call each model's download_models() into the correct subdir.
python3 -c "
import os
from pathlib import Path

target = os.environ['DOCLING_ARTIFACTS_PATH']
Path(target).mkdir(parents=True, exist_ok=True)

# 1. Layout model (docling-layout-heron)
from docling.models.stages.layout.layout_model import LayoutModel
layout_dir = Path(target) / 'docling-project--docling-layout-heron'
layout_dir.mkdir(parents=True, exist_ok=True)
print('  Downloading layout model...')
LayoutModel.download_models(local_dir=layout_dir, progress=True)

# 2. Table structure model (docling-models)
from docling.models.stages.table_structure.table_structure_model import TableStructureModel
table_dir = Path(target) / 'docling-project--docling-models'
table_dir.mkdir(parents=True, exist_ok=True)
print('  Downloading table structure model...')
TableStructureModel.download_models(local_dir=table_dir, progress=True)

# 3. OCR model (RapidOCR)
from docling.models.stages.ocr.rapid_ocr_model import RapidOcrModel
ocr_dir = Path(target) / 'RapidOcr'
ocr_dir.mkdir(parents=True, exist_ok=True)
print('  Downloading OCR model...')
RapidOcrModel.download_models(backend='onnxruntime', local_dir=ocr_dir, progress=True)

print('  All models downloaded.')
"

# ── Verify by running a single conversion ─────────────────
# This warms up the converter and confirms everything is cached.
FIXTURE="qa/fixtures/XECMFNDv16_OpenText Extended ECM for SAP Solutions Foundation v16 Certificate.pdf"
if [ ! -f "$FIXTURE" ]; then
    echo "  WARNING: fixture PDF not found at $FIXTURE"
    echo "  Run from project root with QA fixtures in place."
    exit 1
fi

echo ""
echo "  Verifying offline converter..."
python3 -c "
import os
os.environ['DOCLING_ARTIFACTS_PATH'] = '$PWD/$MODELS_DIR'
from ingest.docling_utils import get_docling_converter
conv = get_docling_converter()
result = conv.convert('$FIXTURE')
print('  Converter verified successfully.')
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
