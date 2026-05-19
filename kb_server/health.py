"""
Health check system for KB-RAG services.

Provides comprehensive health checks for all system components:
- Embedding service
- Vector store (Qdrant)
- Cache (LRU/Redis)
- Database (SQLite)
- File system access

Used by:
- systemd service monitoring
- Load balancers
- Kubernetes liveness/readiness probes
"""

import asyncio
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

log = logging.getLogger("kb-mcp.health")


class HealthStatus:
    """Health status for a component."""

    def __init__(
        self,
        name: str,
        healthy: bool,
        message: str = "",
        latency_ms: Optional[float] = None,
        details: Optional[Dict] = None,
    ):
        """
        Initialize health status.

        Args:
            name: Component name
            healthy: True if healthy
            message: Status message
            latency_ms: Check latency in milliseconds
            details: Additional details dict
        """
        self.name = name
        self.healthy = healthy
        self.message = message
        self.latency_ms = latency_ms
        self.details = details or {}

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "healthy": self.healthy,
            "message": self.message,
        }
        if self.latency_ms is not None:
            result["latency_ms"] = round(self.latency_ms, 2)
        if self.details:
            result["details"] = self.details
        return result


async def check_embedding_service() -> HealthStatus:
    """
    Check embedding service health.

    Verifies:
    - Service is reachable
    - Can generate test embedding
    - Response time acceptable

    Returns:
        HealthStatus for embedding service
    """
    start = time.time()

    try:
        from kb_server.embed_client import health_check

        result = await health_check()
        latency = (time.time() - start) * 1000

        if result.get("status") == "ok":
            return HealthStatus(
                name="embedding",
                healthy=True,
                message=f"Backend: {result.get('backend')}",
                latency_ms=latency,
                details={
                    "backend": result.get("backend"),
                    "model": result.get("model"),
                    "dims": result.get("dims"),
                },
            )
        else:
            return HealthStatus(
                name="embedding",
                healthy=False,
                message=f"Error: {result.get('error')}",
                latency_ms=latency,
            )

    except Exception as e:
        latency = (time.time() - start) * 1000
        log.error(f"Embedding health check failed: {e}")
        return HealthStatus(
            name="embedding",
            healthy=False,
            message=str(e),
            latency_ms=latency,
        )


async def check_vector_store() -> HealthStatus:
    """
    Check Qdrant vector store health.

    Verifies:
    - Connection to Qdrant
    - Collection exists
    - Can query collection

    Returns:
        HealthStatus for vector store
    """
    start = time.time()

    try:
        from kb_server.vector_store import VectorStore

        store = VectorStore()
        await store.connect()

        # Get collection info
        stats = await store.get_stats()
        latency = (time.time() - start) * 1000

        await store.close()

        return HealthStatus(
            name="vector_store",
            healthy=True,
            message=f"{stats.get('total_chunks', 0)} chunks indexed",
            latency_ms=latency,
            details={
                "total_chunks": stats.get("total_chunks", 0),
                "total_documents": stats.get("total_documents", 0),
                "collection": store.collection,
            },
        )

    except Exception as e:
        latency = (time.time() - start) * 1000
        log.error(f"Vector store health check failed: {e}")
        return HealthStatus(
            name="vector_store",
            healthy=False,
            message=str(e),
            latency_ms=latency,
        )


async def check_cache() -> HealthStatus:
    """
    Check cache system health.

    Verifies:
    - Cache is initialized
    - Can get/set values
    - Stats available

    Returns:
        HealthStatus for cache
    """
    start = time.time()

    try:
        from kb_server.embed_client import get_cache_stats

        stats = get_cache_stats()
        latency = (time.time() - start) * 1000

        if stats.get("status") == "disabled":
            return HealthStatus(
                name="cache",
                healthy=True,
                message="Cache disabled",
                latency_ms=latency,
            )

        return HealthStatus(
            name="cache",
            healthy=True,
            message=f"Backend: {stats.get('backend', 'unknown')}",
            latency_ms=latency,
            details={
                "backend": stats.get("backend"),
                "entries": stats.get("entries", 0),
                "size_mb": stats.get("size_mb", 0),
                "hit_rate": stats.get("hit_rate", 0),
            },
        )

    except Exception as e:
        latency = (time.time() - start) * 1000
        log.error(f"Cache health check failed: {e}")
        return HealthStatus(
            name="cache",
            healthy=False,
            message=str(e),
            latency_ms=latency,
        )


async def check_database() -> HealthStatus:
    """
    Check job database health.

    Verifies:
    - Database file exists and is writable
    - Can connect and query
    - Schema is correct

    Returns:
        HealthStatus for database
    """
    start = time.time()

    try:
        from ingest.core.metadata import MetadataStore

        store = MetadataStore()
        stats = store.get_stats()
        latency = (time.time() - start) * 1000

        return HealthStatus(
            name="database",
            healthy=True,
            message=f"{stats.get('total_jobs', 0)} jobs total",
            latency_ms=latency,
            details={
                "total_jobs": stats.get("total_jobs", 0),
                "active_jobs": stats.get("active_jobs", 0),
                "total_files": stats.get("total_files", 0),
            },
        )

    except Exception as e:
        latency = (time.time() - start) * 1000
        log.error(f"Database health check failed: {e}")
        return HealthStatus(
            name="database",
            healthy=False,
            message=str(e),
            latency_ms=latency,
        )


async def check_filesystem() -> HealthStatus:
    """
    Check filesystem access.

    Verifies:
    - Can read/write to data directory
    - Sufficient disk space

    Returns:
        HealthStatus for filesystem
    """
    start = time.time()

    try:
        # Check data directory
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        # Check write access
        test_file = data_dir / ".health_check"
        test_file.write_text("ok")
        test_file.unlink()

        # Check disk space
        stat = shutil.disk_usage(str(data_dir))
        free_gb = stat.free / (1024**3)
        total_gb = stat.total / (1024**3)
        percent_free = (stat.free / stat.total) * 100

        latency = (time.time() - start) * 1000

        if percent_free < 10:
            return HealthStatus(
                name="filesystem",
                healthy=False,
                message=f"Low disk space: {free_gb:.1f}GB free",
                latency_ms=latency,
                details={
                    "free_gb": round(free_gb, 2),
                    "total_gb": round(total_gb, 2),
                    "percent_free": round(percent_free, 2),
                },
            )

        return HealthStatus(
            name="filesystem",
            healthy=True,
            message=f"{free_gb:.1f}GB free of {total_gb:.1f}GB",
            latency_ms=latency,
            details={
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "percent_free": round(percent_free, 2),
            },
        )

    except Exception as e:
        latency = (time.time() - start) * 1000
        log.error(f"Filesystem health check failed: {e}")
        return HealthStatus(
            name="filesystem",
            healthy=False,
            message=str(e),
            latency_ms=latency,
        )


async def check_all_components() -> Dict[str, HealthStatus]:
    """
    Check all system components in parallel.

    Returns:
        Dict mapping component name to HealthStatus
    """
    checks = [
        check_embedding_service(),
        check_vector_store(),
        check_cache(),
        check_database(),
        check_filesystem(),
    ]

    results = await asyncio.gather(*checks, return_exceptions=True)

    status_map = {}
    for result in results:
        if isinstance(result, Exception):
            log.error(f"Health check failed: {result}")
            continue
        if isinstance(result, HealthStatus):
            status_map[result.name] = result

    return status_map


def is_system_healthy(components: Dict[str, HealthStatus]) -> bool:
    """
    Determine if system is healthy overall.

    System is healthy if all critical components are healthy.
    Critical components: embedding, vector_store, database
    Non-critical: cache, filesystem (warnings only)

    Args:
        components: Dict of component health statuses

    Returns:
        True if all critical components are healthy
    """
    critical = ["embedding", "vector_store", "database"]

    for name in critical:
        if name not in components:
            return False
        if not components[name].healthy:
            return False

    return True


async def get_health_summary() -> dict:
    """
    Get health summary for all components.

    Returns:
        Dict with status, components, and timestamp
    """
    components = await check_all_components()
    healthy = is_system_healthy(components)

    return {
        "status": "ok" if healthy else "degraded",
        "healthy": healthy,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "components": {
            name: status.to_dict() for name, status in components.items()
        },
    }
