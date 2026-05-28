# ─────────────────────────────────────────────────────────────
# Remove advanced PDF extraction (docling) and its unique
# dependencies, restoring PyMuPDF as the sole PDF engine.
#
# Usage:
#   .\scripts\remove-pdf-extras.ps1            # just docling + unique deps
#   .\scripts\remove-pdf-extras.ps1 -Purge     # also drop CUDA torch
#
# The -Purge flag additionally removes CUDA/nvidia packages
# and reinstalls CPU-only PyTorch (torch is still required by
# sentence-transformers for the reranker).
# ─────────────────────────────────────────────────────────────

param([switch]$Purge = $false)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "=== kb-rag-mcp: Remove PDF Extras ==="
Write-Host ""

# ── Step 1: Remove docling and its unique dependencies ──────
Write-Host "  Removing docling and unique dependencies..."
$packages = @(
    "docling",
    "docling-core",
    "docling-slim",
    "docling-ibm-models",
    "docling-parse",
    "rapidocr",
    "opencv-python"
)
foreach ($pkg in $packages) {
    pip uninstall -y $pkg 2>$null
}

Write-Host ""
Write-Host "  ✓ docling packages removed."
Write-Host "  ✓ PyMuPDF remains as the PDF fallback engine."
Write-Host ""

# ── Step 2: (optional) Remove CUDA bloat ────────────────────
if ($Purge) {
    Write-Host "  -Purge: Removing CUDA/nvidia packages and reinstalling CPU-only torch..."
    Write-Host "  (torch is still needed by sentence-transformers for reranking)"
    Write-Host ""

    $cudaPackages = @(
        "cuda-bindings",
        "cuda-pathfinder",
        "cuda-toolkit",
        "nvidia-cublas",
        "nvidia-cuda-cupti",
        "nvidia-cuda-nvrtc",
        "nvidia-cuda-runtime",
        "nvidia-cudnn-cu13",
        "nvidia-cufft",
        "nvidia-cufile",
        "nvidia-curand",
        "nvidia-cusolver",
        "nvidia-cusparse",
        "nvidia-cusparselt-cu13",
        "nvidia-nccl-cu13",
        "nvidia-nvjitlink",
        "nvidia-nvshmem-cu13",
        "nvidia-nvtx",
        "triton"
    )
    foreach ($pkg in $cudaPackages) {
        pip uninstall -y $pkg 2>$null
    }

    # Reinstall CPU-only torch (sentence-transformers needs it for reranker)
    pip install torch torchvision `
        --index-url https://download.pytorch.org/whl/cpu

    Write-Host ""
    Write-Host "  ✓ CUDA packages removed, CPU-only torch reinstalled."
    Write-Host ""
}

Write-Host "=== Done ==="
Write-Host "PDF extraction will now use PyMuPDF (fitz)."
