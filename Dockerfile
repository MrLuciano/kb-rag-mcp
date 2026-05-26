# ── Stage 1: build ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools for native extensions (fastembed, sentence-transformers)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for layer caching
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system deps (wget for healthcheck, libgomp for fastembed ONNX)
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY config/      ./config/
COPY kb_server/   ./kb_server/
COPY ingest/      ./ingest/
COPY observability/ ./observability/
COPY scripts/docker-entrypoint.sh /app/
COPY setup.py     .

# Install the package itself (no deps — already installed)
RUN pip install --no-cache-dir --no-deps -e .

# Create data directories
RUN mkdir -p /app/data/qdrant /app/logs

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Healthcheck via the built-in HTTP health server (port 8080 by default)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \

    CMD wget --spider -q http://localhost:${HEALTH_PORT:-8080}/health || exit 1

# Expose ports: MCP SSE (8765), health/metrics HTTP (8080)
ENV PYTHONUNBUFFERED=1
EXPOSE 8765 8080

# Use entrypoint script to start both health server and MCP server
ENTRYPOINT ["/app/docker-entrypoint.sh"]
