# ─────────────────────────────────────────────────────────────
# Install advanced PDF extraction (docling) with hardware-aware
# dependency resolution (Windows / PowerShell).
#
# Usage:
#   .\scripts\install-pdf-extras.ps1
#
# On machines with an NVIDIA GPU, docling + default (CUDA) PyTorch
# are installed. On all other machines (AMD, Intel, CPU-only), CPU-
# only PyTorch is used, avoiding ~1 GB of useless CUDA/NVIDIA packages.
# ─────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "=== kb-rag-mcp: PDF Extras Install ==="
Write-Host ""

# ── Detect GPU ────────────────────────────────────────────────
$hasNvidia = $false
try {
    $null = nvidia-smi 2>&1
    $hasNvidia = $true
} catch {
    $hasNvidia = $false
}

if ($hasNvidia) {
    Write-Host "  NVIDIA GPU detected — installing docling with CUDA PyTorch."
    pip install -e ".[pdf]"
} else {
    Write-Host "  No NVIDIA GPU detected — installing docling with CPU-only PyTorch."
    Write-Host "  (This avoids ~1 GB of unnecessary CUDA/NVIDIA packages.)"
    Write-Host ""

    # CPU-only PyTorch first, then docling
    pip install torch torchvision `
        --index-url https://download.pytorch.org/whl/cpu

    pip install -e ".[pdf]"
}

Write-Host ""
Write-Host "=== Done ==="
Write-Host 'To verify: python -c "from docling.document_converter import DocumentConverter; print(''docling OK'')"'
