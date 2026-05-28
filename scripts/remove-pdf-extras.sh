#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Remove advanced PDF extraction (docling) and its unique
# dependencies, restoring PyMuPDF as the sole PDF engine.
#
# Usage:
#   ./scripts/remove-pdf-extras.sh            # just docling + unique deps
#   ./scripts/remove-pdf-extras.sh --purge    # also drop CUDA torch
#
# The --purge flag additionally removes CUDA/nvidia packages
# and reinstalls CPU-only PyTorch (torch is still required by
# sentence-transformers for the reranker).
# ─────────────────────────────────────────────────────────────
set -euo pipefail

PURGE=false
if [ "${1:-}" = "--purge" ]; then
    PURGE=true
fi

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "=== kb-rag-mcp: Remove PDF Extras ==="
echo ""

# ── Step 1: Remove docling and its unique dependencies ──────
echo "  Removing docling and unique dependencies..."
pip uninstall -y \
    docling \
    docling-core \
    docling-slim \
    docling-ibm-models \
    docling-parse \
    rapidocr \
    opencv-python \
    2>/dev/null || true

echo ""
echo "  ✓ docling packages removed."
echo "  ✓ PyMuPDF remains as the PDF fallback engine."
echo ""

# ── Step 2: (optional) Remove CUDA bloat ────────────────────
if [ "$PURGE" = true ]; then
    echo "  --purge: Removing CUDA/nvidia packages and reinstalling CPU-only torch..."
    echo "  (torch is still needed by sentence-transformers for reranking)"
    echo ""

    pip uninstall -y \
        cuda-bindings \
        cuda-pathfinder \
        cuda-toolkit \
        nvidia-cublas \
        nvidia-cuda-cupti \
        nvidia-cuda-nvrtc \
        nvidia-cuda-runtime \
        nvidia-cudnn-cu13 \
        nvidia-cufft \
        nvidia-cufile \
        nvidia-curand \
        nvidia-cusolver \
        nvidia-cusparse \
        nvidia-cusparselt-cu13 \
        nvidia-nccl-cu13 \
        nvidia-nvjitlink \
        nvidia-nvshmem-cu13 \
        nvidia-nvtx \
        triton \
        2>/dev/null || true

    # Reinstall CPU-only torch (sentence-transformers needs it for reranker)
    pip install torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu

    echo ""
    echo "  ✓ CUDA packages removed, CPU-only torch reinstalled."
    echo ""
fi

echo "=== Done ==="
echo "PDF extraction will now use PyMuPDF (fitz)."
