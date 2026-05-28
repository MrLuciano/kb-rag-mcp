#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Install advanced PDF extraction (docling) with hardware-aware
# dependency resolution.
#
# Usage:
#   ./scripts/install-pdf-extras.sh
#
# On machines with an NVIDIA GPU, docling + default (CUDA) PyTorch
# are installed. On all other machines (AMD, Intel, CPU-only), CPU-
# only PyTorch is used, avoiding ~1 GB of useless CUDA/NVIDIA packages.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

# ── Detect GPU ────────────────────────────────────────────────
HAS_NVIDIA=false
if command -v nvidia-smi &>/dev/null; then
    if nvidia-smi &>/dev/null; then
        HAS_NVIDIA=true
    fi
fi

echo "=== kb-rag-mcp: PDF Extras Install ==="
echo ""

if [ "$HAS_NVIDIA" = true ]; then
    echo "  NVIDIA GPU detected — installing docling with CUDA PyTorch."
    pip install -e ".[pdf]"
else
    echo "  No NVIDIA GPU detected — installing docling with CPU-only PyTorch."
    echo "  (This avoids ~1 GB of unnecessary CUDA/NVIDIA packages.)"
    echo ""

    # Install CPU-only PyTorch first, then docling.
    # Pre-installing CPU torch prevents pip from fetching the CUDA variant
    # when resolving docling's dependencies.
    pip install torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu

    # Now install docling — pip sees torch is already satisfied and skips it.
    pip install -e ".[pdf]"
fi

echo ""
echo "=== Done ==="
echo "To verify: python3 -c \"from docling.document_converter import DocumentConverter; print('docling OK')\""
