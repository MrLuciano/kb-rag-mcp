#!/bin/bash
# Docker entrypoint script for kb-rag-mcp container
# Starts both the health/metrics HTTP server and the MCP SSE server

set -e

# Default ports
HEALTH_PORT="${HEALTH_PORT:-8080}"
SSE_PORT="${SSE_PORT:-8765}"

echo "[entrypoint] Starting kb-rag-mcp services..."
echo "[entrypoint] Health server will listen on port ${HEALTH_PORT}"
echo "[entrypoint] MCP SSE server will listen on port ${SSE_PORT}"

# GPU detection — install GPU-accelerated packages based on GPU vendor
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
    echo "[entrypoint] NVIDIA GPU detected — installing CUDA-accelerated packages"
    pip install --no-cache-dir -r /app/requirements.gpu.txt || \
        echo "[entrypoint] WARNING: GPU package install failed — continuing without GPU acceleration"
elif command -v rocm-smi &> /dev/null && rocm-smi &> /dev/null; then
    echo "[entrypoint] AMD GPU detected — installing ROCm-accelerated packages"
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/rocm6.2 && \
    pip install --no-cache-dir sentence-transformers || \
        echo "[entrypoint] WARNING: GPU package install failed — continuing without GPU acceleration"
else
    echo "[entrypoint] No supported GPU detected — using CPU-only configuration"
fi

# Start health/metrics HTTP server in background
echo "[entrypoint] Starting health server..."
python -m kb_server.health_server &
HEALTH_PID=$!
echo "[entrypoint] Health server started (PID: ${HEALTH_PID})"

# Give health server a moment to bind to port
sleep 2

# Start MCP server in foreground (this process becomes PID 1's child)
echo "[entrypoint] Starting MCP SSE server..."
exec python -m kb_server.server
