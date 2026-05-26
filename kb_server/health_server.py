"""
Health check HTTP server for KB-RAG.

Provides HTTP endpoints for health checks that can be used by:
- systemd service monitoring
- Load balancers
- Monitoring systems

This runs as a separate lightweight service alongside the main MCP server.
"""

import logging
import os
import sys
from pathlib import Path

# ── Load .env before any os.getenv
from config.bootstrap_env import bootstrap_env
bootstrap_env()

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

# Import metrics module to register all metrics with prometheus_client
import observability.metrics  # noqa: F401

from kb_server.health import (
    check_all_components,
    get_health_summary,
)

# ── Logging ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(
            os.getenv("LOG_PATH", "/tmp/kb-mcp-health.log")
        ),
    ],
)
log = logging.getLogger("kb-mcp.health-server")

# ── Config ─────────────────────────────────────────────────────
HEALTH_HOST = os.getenv("HEALTH_HOST", "127.0.0.1")
HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8000"))

# ── App ────────────────────────────────────────────────────────
app = FastAPI(
    title="KB-RAG Health Check",
    description="Health check endpoints for KB-RAG services",
    version="1.0.0",
)


@app.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns 200 if system is operational.
    Used by: load balancers, monitoring systems
    """
    return {"status": "ok", "service": "kb-rag"}


@app.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with component status.

    Returns comprehensive status of all components.
    """
    return await get_health_summary()


@app.get("/ready")
async def readiness_check():
    """
    Kubernetes-style readiness check.

    Returns 200 if service is ready to accept traffic.
    Returns 503 if service is not ready.
    """
    components = await check_all_components()

    # Service is ready if critical components are healthy
    critical = ["embedding", "vector_store", "database"]
    ready = all(
        name in components and components[name].healthy
        for name in critical
    )

    if ready:
        return {"ready": True}
    else:
        return JSONResponse(
            content={"ready": False},
            status_code=503,
        )


@app.get("/alive")
async def liveness_check():
    """
    Kubernetes-style liveness check.

    Returns 200 if service process is alive.
    Always returns 200 (if we can respond, we're alive).
    """
    return {"alive": True}


@app.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.
    
    Returns all metrics in Prometheus text format.
    Used by: Prometheus scraper
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    log.info(f"Starting health check server on {HEALTH_HOST}:{HEALTH_PORT}")
    uvicorn.run(
        app,
        host=HEALTH_HOST,
        port=HEALTH_PORT,
        log_config=None,  # Use our logging config
    )
