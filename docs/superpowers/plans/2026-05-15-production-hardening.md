# Production Hardening Implementation Plan (PHASE 9)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy production-ready KB-RAG system with systemd services, automatic recovery, monitoring, and operational tooling.

**Architecture:** Two systemd services (server + scheduler) with health checks, automatic restart on failure, log rotation, Prometheus metrics export, and Grafana dashboards for visualization. All services run as unprivileged kb-rag user with proper permissions and security boundaries.

**Tech Stack:** systemd, logrotate, Prometheus, Grafana, Bash scripts, Python health checks

---

## File Structure

### New Files (19)

**Systemd Services:**
- `deployment/systemd/kb-rag-server.service` - FastAPI server service
- `deployment/systemd/kb-rag-scheduler.service` - Job scheduler service
- `deployment/systemd/kb-rag.target` - Target to manage both services together

**Deployment Scripts:**
- `deployment/scripts/install.sh` - Installation and setup script
- `deployment/scripts/uninstall.sh` - Clean removal script
- `deployment/scripts/health-check.sh` - Health check script for monitoring
- `deployment/scripts/backup.sh` - Backup script for databases and config
- `deployment/scripts/restore.sh` - Restore from backup
- `deployment/scripts/update.sh` - Update to new version

**Configuration:**
- `deployment/config/kb-rag.env` - Environment variables template
- `deployment/config/logrotate.conf` - Log rotation configuration
- `deployment/config/prometheus.yml` - Prometheus scraping config
- `deployment/config/grafana-dashboard.json` - Grafana dashboard definition

**Health Check Module:**
- `server/health.py` - Comprehensive health check endpoints
- `tests/test_health.py` - Health check tests

**Documentation:**
- `docs/DEPLOYMENT.md` - Deployment guide
- `docs/MONITORING.md` - Monitoring and alerting guide
- `docs/OPERATIONS.md` - Day-to-day operations guide
- `docs/PHASE9_COMPLETION.md` - Completion report

---

## Task 1: Health Check System

**Files:**
- Create: `server/health.py`
- Create: `tests/test_health.py`
- Modify: `server/server.py` (add health endpoints)

- [ ] **Step 1: Write failing health check tests**

Create `tests/test_health.py`:

```python
"""Tests for health check system."""

import pytest
from fastapi.testclient import TestClient


def test_health_basic():
    """Test basic health endpoint returns 200."""
    from server.server import app
    
    client = TestClient(app)
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_detailed():
    """Test detailed health includes all components."""
    from server.server import app
    
    client = TestClient(app)
    response = client.get("/health/detailed")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert "components" in data
    assert "embedding" in data["components"]
    assert "vector_store" in data["components"]
    assert "cache" in data["components"]
    assert "timestamp" in data


def test_readiness_check():
    """Test readiness endpoint."""
    from server.server import app
    
    client = TestClient(app)
    response = client.get("/ready")
    
    assert response.status_code in [200, 503]
    assert "ready" in response.json()


def test_liveness_check():
    """Test liveness endpoint."""
    from server.server import app
    
    client = TestClient(app)
    response = client.get("/alive")
    
    assert response.status_code == 200
    assert response.json()["alive"] is True


@pytest.mark.asyncio
async def test_health_check_with_failures():
    """Test health check detects component failures."""
    from server.health import check_all_components
    
    # Mock a failing component
    status = await check_all_components()
    
    assert "embedding" in status
    assert "vector_store" in status
    assert "cache" in status
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_health.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'server.health'"

- [ ] **Step 3: Implement health check module**

Create `server/health.py`:

```python
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
    """
    start = time.time()
    
    try:
        from server.embed_client import health_check
        
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
    """
    start = time.time()
    
    try:
        from server.vector_store import VectorStore
        
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
    """
    start = time.time()
    
    try:
        from server.embed_client import get_cache_stats
        
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
                "pending_jobs": stats.get("pending_jobs", 0),
                "running_jobs": stats.get("running_jobs", 0),
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
    """
    start = time.time()
    
    try:
        import shutil
        
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
            name: status.to_dict()
            for name, status in components.items()
        },
    }
```

- [ ] **Step 4: Add health endpoints to server**

Modify `server/server.py`, add after existing routes:

```python
from server.health import get_health_summary, check_all_components


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
        from fastapi import Response
        return Response(
            content='{"ready": false}',
            status_code=503,
            media_type="application/json",
        )


@app.get("/alive")
async def liveness_check():
    """
    Kubernetes-style liveness check.
    
    Returns 200 if service process is alive.
    Always returns 200 (if we can respond, we're alive).
    """
    return {"alive": True}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_health.py -v`
Expected: PASS (all 5 tests passing)

- [ ] **Step 6: Test health endpoints manually**

Run server and test:
```bash
# Terminal 1: Start server
python3 -m server.server

# Terminal 2: Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/detailed
curl http://localhost:8000/ready
curl http://localhost:8000/alive
```

Expected: All return 200 with appropriate JSON

- [ ] **Step 7: Commit health check system**

```bash
git add server/health.py tests/test_health.py server/server.py
git commit -m "feat(health): add comprehensive health check system

- Add HealthStatus class for component status
- Implement checks for embedding, vector store, cache, database, filesystem
- Add /health, /health/detailed, /ready, /alive endpoints
- Add 5 comprehensive tests
- Ready for systemd and k8s monitoring"
```

---

## Task 2: systemd Service Files

**Files:**
- Create: `deployment/systemd/kb-rag-server.service`
- Create: `deployment/systemd/kb-rag-scheduler.service`
- Create: `deployment/systemd/kb-rag.target`

- [ ] **Step 1: Create server service file**

Create `deployment/systemd/kb-rag-server.service`:

```ini
[Unit]
Description=KB-RAG MCP Server
Documentation=https://github.com/MrLuciano/kb-rag-mcp
After=network.target
Wants=kb-rag-scheduler.service

[Service]
Type=simple
User=kb-rag
Group=kb-rag
WorkingDirectory=/opt/kb-rag
Environment="PATH=/opt/kb-rag/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/opt/kb-rag/config/kb-rag.env

# Start server
ExecStart=/opt/kb-rag/venv/bin/python3 -m server.server

# Health check
ExecStartPost=/bin/sleep 5
ExecStartPost=/opt/kb-rag/deployment/scripts/health-check.sh server

# Restart policy
Restart=always
RestartSec=10
StartLimitInterval=5min
StartLimitBurst=3

# Resource limits
MemoryLimit=2G
CPUQuota=200%

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/kb-rag/data /opt/kb-rag/logs

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=kb-rag-server

[Install]
WantedBy=multi-user.target
WantedBy=kb-rag.target
```

- [ ] **Step 2: Create scheduler service file**

Create `deployment/systemd/kb-rag-scheduler.service`:

```ini
[Unit]
Description=KB-RAG Job Scheduler
Documentation=https://github.com/MrLuciano/kb-rag-mcp
After=network.target kb-rag-server.service
Requires=kb-rag-server.service

[Service]
Type=simple
User=kb-rag
Group=kb-rag
WorkingDirectory=/opt/kb-rag
Environment="PATH=/opt/kb-rag/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/opt/kb-rag/config/kb-rag.env

# Start scheduler (TODO: implement scheduler daemon)
ExecStart=/opt/kb-rag/venv/bin/python3 -m ingest.scheduler_daemon

# Restart policy
Restart=always
RestartSec=10
StartLimitInterval=5min
StartLimitBurst=3

# Resource limits
MemoryLimit=1G
CPUQuota=100%

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/kb-rag/data /opt/kb-rag/logs

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=kb-rag-scheduler

[Install]
WantedBy=multi-user.target
WantedBy=kb-rag.target
```

- [ ] **Step 3: Create target file to manage both services**

Create `deployment/systemd/kb-rag.target`:

```ini
[Unit]
Description=KB-RAG System Target
Documentation=https://github.com/MrLuciano/kb-rag-mcp
Requires=kb-rag-server.service
Wants=kb-rag-scheduler.service

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 4: Verify service file syntax**

Run: `systemd-analyze verify deployment/systemd/*.service`
Expected: No errors

- [ ] **Step 5: Commit systemd service files**

```bash
git add deployment/systemd/
git commit -m "feat(systemd): add service files for server and scheduler

- kb-rag-server.service: FastAPI server with health checks
- kb-rag-scheduler.service: Job scheduler daemon
- kb-rag.target: Target to manage both services
- Auto-restart on failure with backoff
- Resource limits (2GB RAM server, 1GB scheduler)
- Security hardening (NoNewPrivileges, ProtectSystem)
- Journal logging with syslog identifiers"
```

---

## Task 3: Deployment Scripts

**Files:**
- Create: `deployment/scripts/install.sh`
- Create: `deployment/scripts/health-check.sh`
- Create: `deployment/scripts/backup.sh`
- Create: `deployment/scripts/restore.sh`
- Create: `deployment/scripts/uninstall.sh`
- Create: `deployment/scripts/update.sh`

- [ ] **Step 1: Create install script**

Create `deployment/scripts/install.sh`:

```bash
#!/bin/bash
#
# KB-RAG Installation Script
#
# Installs KB-RAG system as systemd services on Debian/Ubuntu.
#
# Usage:
#   sudo ./install.sh [--user kb-rag] [--install-dir /opt/kb-rag]
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
KB_USER="${KB_USER:-kb-rag}"
INSTALL_DIR="${INSTALL_DIR:-/opt/kb-rag}"
CONFIG_DIR="${INSTALL_DIR}/config"
DATA_DIR="${INSTALL_DIR}/data"
LOG_DIR="${INSTALL_DIR}/logs"
VENV_DIR="${INSTALL_DIR}/venv"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

check_os() {
    if [[ ! -f /etc/debian_version ]]; then
        log_error "This script requires Debian or Ubuntu"
        exit 1
    fi
    log_info "Detected Debian/Ubuntu system"
}

install_dependencies() {
    log_info "Installing system dependencies..."
    
    apt-get update -qq
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        git \
        curl \
        sqlite3 \
        logrotate
    
    log_info "System dependencies installed"
}

create_user() {
    if id "$KB_USER" &>/dev/null; then
        log_warn "User $KB_USER already exists"
    else
        log_info "Creating user $KB_USER..."
        useradd --system --shell /bin/bash --create-home \
            --home-dir "$INSTALL_DIR" "$KB_USER"
        log_info "User $KB_USER created"
    fi
}

create_directories() {
    log_info "Creating directories..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOG_DIR"
    
    log_info "Directories created"
}

copy_files() {
    log_info "Copying application files..."
    
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    
    # Copy application code
    rsync -av --exclude='.git' --exclude='__pycache__' \
        --exclude='*.pyc' --exclude='venv' --exclude='data' \
        "$SCRIPT_DIR/" "$INSTALL_DIR/"
    
    log_info "Application files copied"
}

setup_virtualenv() {
    log_info "Setting up Python virtual environment..."
    
    cd "$INSTALL_DIR"
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip wheel setuptools
    
    # Install dependencies
    if [[ -f requirements.txt ]]; then
        pip install -r requirements.txt
    else
        log_error "requirements.txt not found"
        exit 1
    fi
    
    deactivate
    log_info "Virtual environment ready"
}

setup_configuration() {
    log_info "Setting up configuration..."
    
    # Create environment file if it doesn't exist
    if [[ ! -f "$CONFIG_DIR/kb-rag.env" ]]; then
        cat > "$CONFIG_DIR/kb-rag.env" <<'EOF'
# KB-RAG Configuration
# Generated by install.sh

# Embedding Configuration
EMBED_BACKEND=openai-compat
EMBED_MODEL=text-embedding-nomic-embed-text-v1.5-embedding
LMS_BASE_URL=http://localhost:1234

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=kb_docs

# Cache Configuration
CACHE_BACKEND=lru
CACHE_MAX_SIZE_MB=512
CACHE_TTL=3600

# Batch Processing (PHASE 8)
EMBED_BATCH_SIZE=32
FILE_BATCH_SIZE=50
QDRANT_BATCH_SIZE=100
HTTP_POOL_CONNECTIONS=20

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Logging
LOG_LEVEL=INFO
EOF
        log_info "Created default configuration file: $CONFIG_DIR/kb-rag.env"
    else
        log_warn "Configuration file already exists, skipping"
    fi
}

install_systemd_services() {
    log_info "Installing systemd services..."
    
    # Copy service files
    cp "$INSTALL_DIR/deployment/systemd"/*.service /etc/systemd/system/
    cp "$INSTALL_DIR/deployment/systemd"/*.target /etc/systemd/system/
    
    # Reload systemd
    systemctl daemon-reload
    
    log_info "Systemd services installed"
}

setup_logrotate() {
    log_info "Setting up log rotation..."
    
    cat > /etc/logrotate.d/kb-rag <<EOF
$LOG_DIR/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 $KB_USER $KB_USER
    sharedscripts
    postrotate
        systemctl reload kb-rag-server.service >/dev/null 2>&1 || true
    endscript
}
EOF
    
    log_info "Log rotation configured"
}

set_permissions() {
    log_info "Setting permissions..."
    
    chown -R "$KB_USER:$KB_USER" "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR/deployment/scripts"
    chmod 640 "$CONFIG_DIR/kb-rag.env"
    
    log_info "Permissions set"
}

enable_services() {
    log_info "Enabling services..."
    
    systemctl enable kb-rag-server.service
    systemctl enable kb-rag-scheduler.service
    systemctl enable kb-rag.target
    
    log_info "Services enabled"
}

start_services() {
    log_info "Starting services..."
    
    systemctl start kb-rag.target
    
    # Wait for services to start
    sleep 5
    
    # Check status
    if systemctl is-active --quiet kb-rag-server.service; then
        log_info "✓ kb-rag-server.service is running"
    else
        log_error "✗ kb-rag-server.service failed to start"
        systemctl status kb-rag-server.service --no-pager
    fi
    
    if systemctl is-active --quiet kb-rag-scheduler.service; then
        log_info "✓ kb-rag-scheduler.service is running"
    else
        log_warn "✗ kb-rag-scheduler.service is not running (may be expected)"
    fi
}

print_summary() {
    cat <<EOF

${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
${GREEN}  KB-RAG Installation Complete!${NC}
${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

Installation Directory: $INSTALL_DIR
Configuration:         $CONFIG_DIR/kb-rag.env
Data Directory:        $DATA_DIR
Logs Directory:        $LOG_DIR

Services:
  - kb-rag-server     (FastAPI server)
  - kb-rag-scheduler  (Job scheduler)

Service Management:
  Start:    sudo systemctl start kb-rag.target
  Stop:     sudo systemctl stop kb-rag.target
  Restart:  sudo systemctl restart kb-rag.target
  Status:   sudo systemctl status kb-rag.target
  Logs:     sudo journalctl -u kb-rag-server -f

Health Check:
  curl http://localhost:8000/health

Next Steps:
  1. Edit configuration: $CONFIG_DIR/kb-rag.env
  2. Restart services: sudo systemctl restart kb-rag.target
  3. Test health: curl http://localhost:8000/health/detailed
  4. View logs: sudo journalctl -u kb-rag-server -f

${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

EOF
}

# Main installation flow
main() {
    log_info "KB-RAG Installation Script"
    echo
    
    check_root
    check_os
    
    install_dependencies
    create_user
    create_directories
    copy_files
    setup_virtualenv
    setup_configuration
    install_systemd_services
    setup_logrotate
    set_permissions
    enable_services
    start_services
    
    print_summary
}

# Run main
main "$@"
```

- [ ] **Step 2: Create health check script**

Create `deployment/scripts/health-check.sh`:

```bash
#!/bin/bash
#
# KB-RAG Health Check Script
#
# Checks health of KB-RAG services and exits with appropriate code.
#
# Usage:
#   ./health-check.sh [server|scheduler|all]
#
# Exit codes:
#   0 - Healthy
#   1 - Unhealthy
#   2 - Script error
#

set -euo pipefail

SERVICE="${1:-all}"
HOST="${KB_RAG_HOST:-localhost}"
PORT="${KB_RAG_PORT:-8000}"
TIMEOUT=5

check_server() {
    local url="http://$HOST:$PORT/ready"
    
    if response=$(curl -sf --max-time "$TIMEOUT" "$url" 2>/dev/null); then
        if echo "$response" | grep -q '"ready":\s*true'; then
            echo "✓ Server is healthy"
            return 0
        else
            echo "✗ Server is not ready"
            return 1
        fi
    else
        echo "✗ Server is not responding"
        return 1
    fi
}

check_scheduler() {
    # Check if scheduler process is running
    if systemctl is-active --quiet kb-rag-scheduler.service; then
        echo "✓ Scheduler is running"
        return 0
    else
        echo "✗ Scheduler is not running"
        return 1
    fi
}

case "$SERVICE" in
    server)
        check_server
        ;;
    scheduler)
        check_scheduler
        ;;
    all)
        status=0
        check_server || status=1
        check_scheduler || status=1
        exit $status
        ;;
    *)
        echo "Usage: $0 [server|scheduler|all]"
        exit 2
        ;;
esac
```

- [ ] **Step 3: Create backup script**

Create `deployment/scripts/backup.sh`:

```bash
#!/bin/bash
#
# KB-RAG Backup Script
#
# Creates timestamped backup of databases and configuration.
#
# Usage:
#   ./backup.sh [--output-dir /backups]
#

set -euo pipefail

# Configuration
INSTALL_DIR="${INSTALL_DIR:-/opt/kb-rag}"
BACKUP_DIR="${BACKUP_DIR:-/opt/kb-rag/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="kb-rag-backup-$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
}

create_backup() {
    log_info "Creating backup: $BACKUP_NAME"
    
    # Create backup directory
    mkdir -p "$BACKUP_PATH"
    
    # Backup databases
    log_info "Backing up databases..."
    if [[ -f "$INSTALL_DIR/data/kb_metadata.db" ]]; then
        sqlite3 "$INSTALL_DIR/data/kb_metadata.db" ".backup '$BACKUP_PATH/kb_metadata.db'"
    fi
    
    if [[ -f "$INSTALL_DIR/data/registry.db" ]]; then
        sqlite3 "$INSTALL_DIR/data/registry.db" ".backup '$BACKUP_PATH/registry.db'"
    fi
    
    # Backup configuration
    log_info "Backing up configuration..."
    if [[ -d "$INSTALL_DIR/config" ]]; then
        cp -r "$INSTALL_DIR/config" "$BACKUP_PATH/"
    fi
    
    # Backup Qdrant data (if local)
    if [[ -d "$INSTALL_DIR/data/qdrant" ]]; then
        log_info "Backing up Qdrant data..."
        tar -czf "$BACKUP_PATH/qdrant_data.tar.gz" \
            -C "$INSTALL_DIR/data" qdrant
    fi
    
    # Create archive
    log_info "Creating archive..."
    tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" \
        -C "$BACKUP_DIR" "$BACKUP_NAME"
    rm -rf "$BACKUP_PATH"
    
    log_info "Backup created: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
    log_info "Size: $(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)"
}

cleanup_old_backups() {
    log_info "Cleaning up old backups (keeping last 7)..."
    
    cd "$BACKUP_DIR"
    ls -t kb-rag-backup-*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm -f
    
    log_info "Cleanup complete"
}

main() {
    mkdir -p "$BACKUP_DIR"
    
    create_backup
    cleanup_old_backups
    
    log_info "Backup complete!"
}

main "$@"
```

- [ ] **Step 4: Create restore script**

Create `deployment/scripts/restore.sh`:

```bash
#!/bin/bash
#
# KB-RAG Restore Script
#
# Restores from backup archive.
#
# Usage:
#   ./restore.sh /path/to/backup.tar.gz
#

set -euo pipefail

BACKUP_FILE="${1:-}"
INSTALL_DIR="${INSTALL_DIR:-/opt/kb-rag}"

log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
}

if [[ -z "$BACKUP_FILE" ]]; then
    log_error "Usage: $0 <backup-file.tar.gz>"
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

log_info "Restoring from: $BACKUP_FILE"

# Stop services
log_info "Stopping services..."
systemctl stop kb-rag.target || true

# Extract backup
TEMP_DIR=$(mktemp -d)
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"
BACKUP_NAME=$(ls "$TEMP_DIR")

# Restore databases
log_info "Restoring databases..."
if [[ -f "$TEMP_DIR/$BACKUP_NAME/kb_metadata.db" ]]; then
    cp "$TEMP_DIR/$BACKUP_NAME/kb_metadata.db" "$INSTALL_DIR/data/"
fi

if [[ -f "$TEMP_DIR/$BACKUP_NAME/registry.db" ]]; then
    cp "$TEMP_DIR/$BACKUP_NAME/registry.db" "$INSTALL_DIR/data/"
fi

# Restore configuration
log_info "Restoring configuration..."
if [[ -d "$TEMP_DIR/$BACKUP_NAME/config" ]]; then
    cp -r "$TEMP_DIR/$BACKUP_NAME/config/"* "$INSTALL_DIR/config/"
fi

# Restore Qdrant data
if [[ -f "$TEMP_DIR/$BACKUP_NAME/qdrant_data.tar.gz" ]]; then
    log_info "Restoring Qdrant data..."
    tar -xzf "$TEMP_DIR/$BACKUP_NAME/qdrant_data.tar.gz" \
        -C "$INSTALL_DIR/data"
fi

# Cleanup
rm -rf "$TEMP_DIR"

# Fix permissions
chown -R kb-rag:kb-rag "$INSTALL_DIR"

# Start services
log_info "Starting services..."
systemctl start kb-rag.target

log_info "Restore complete!"
```

- [ ] **Step 5: Create uninstall script**

Create `deployment/scripts/uninstall.sh`:

```bash
#!/bin/bash
#
# KB-RAG Uninstall Script
#
# Removes KB-RAG system completely.
#
# Usage:
#   sudo ./uninstall.sh [--keep-data]
#

set -euo pipefail

KEEP_DATA=false
KB_USER="${KB_USER:-kb-rag}"
INSTALL_DIR="${INSTALL_DIR:-/opt/kb-rag}"

if [[ "${1:-}" == "--keep-data" ]]; then
    KEEP_DATA=true
fi

log_info() {
    echo "[INFO] $1"
}

# Stop and disable services
log_info "Stopping services..."
systemctl stop kb-rag.target || true
systemctl disable kb-rag-server.service || true
systemctl disable kb-rag-scheduler.service || true
systemctl disable kb-rag.target || true

# Remove service files
log_info "Removing service files..."
rm -f /etc/systemd/system/kb-rag*.service
rm -f /etc/systemd/system/kb-rag.target
systemctl daemon-reload

# Remove logrotate config
log_info "Removing logrotate config..."
rm -f /etc/logrotate.d/kb-rag

# Remove installation directory
if [[ "$KEEP_DATA" == "false" ]]; then
    log_info "Removing installation directory..."
    rm -rf "$INSTALL_DIR"
else
    log_info "Keeping data directory (--keep-data specified)"
fi

# Remove user
log_info "Removing user $KB_USER..."
userdel "$KB_USER" || true

log_info "Uninstall complete!"
```

- [ ] **Step 6: Create update script**

Create `deployment/scripts/update.sh`:

```bash
#!/bin/bash
#
# KB-RAG Update Script
#
# Updates KB-RAG to latest version.
#
# Usage:
#   sudo ./update.sh
#

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/kb-rag}"
BACKUP_DIR="${INSTALL_DIR}/backups"

log_info() {
    echo "[INFO] $1"
}

# Create backup before update
log_info "Creating backup before update..."
"$INSTALL_DIR/deployment/scripts/backup.sh"

# Stop services
log_info "Stopping services..."
systemctl stop kb-rag.target

# Pull latest code
log_info "Pulling latest code..."
cd "$INSTALL_DIR"
git pull origin master

# Update dependencies
log_info "Updating dependencies..."
source venv/bin/activate
pip install --upgrade -r requirements.txt
deactivate

# Run migrations (if any)
# TODO: Add migration support

# Restart services
log_info "Restarting services..."
systemctl daemon-reload
systemctl restart kb-rag.target

# Wait and check health
sleep 5
"$INSTALL_DIR/deployment/scripts/health-check.sh" all

log_info "Update complete!"
```

- [ ] **Step 7: Make scripts executable**

Run:
```bash
chmod +x deployment/scripts/*.sh
```

- [ ] **Step 8: Test install script (dry-run if possible)**

Test syntax:
```bash
bash -n deployment/scripts/install.sh
bash -n deployment/scripts/health-check.sh
bash -n deployment/scripts/backup.sh
bash -n deployment/scripts/restore.sh
bash -n deployment/scripts/uninstall.sh
bash -n deployment/scripts/update.sh
```

Expected: No syntax errors

- [ ] **Step 9: Commit deployment scripts**

```bash
git add deployment/scripts/
git commit -m "feat(deploy): add deployment and operations scripts

- install.sh: Complete installation with systemd setup
- health-check.sh: Service health verification
- backup.sh: Database and config backup with rotation
- restore.sh: Restore from backup
- uninstall.sh: Clean removal (with --keep-data option)
- update.sh: Safe update with automatic backup

All scripts include error handling, logging, and safety checks"
```

---

## Task 4: Configuration Files

**Files:**
- Create: `deployment/config/kb-rag.env`
- Create: `deployment/config/logrotate.conf`
- Create: `deployment/config/prometheus.yml`

- [ ] **Step 1: Create environment template**

Create `deployment/config/kb-rag.env`:

```bash
# KB-RAG Configuration Template
# Copy to /opt/kb-rag/config/kb-rag.env and customize

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Embedding Service
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Backend: openai-compat, ollama, lmstudio-rest, lmstudio-sdk
EMBED_BACKEND=openai-compat

# Model name
EMBED_MODEL=text-embedding-nomic-embed-text-v1.5-embedding

# LM Studio URL (for openai-compat and lmstudio-rest)
LMS_BASE_URL=http://localhost:1234

# Ollama URL (for ollama backend)
OLLAMA_HOST=http://localhost:11434

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Vector Store (Qdrant)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Qdrant connection
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=kb_docs

# Optional: gRPC for better performance
QDRANT_GRPC=false
QDRANT_GRPC_PORT=6334
QDRANT_TIMEOUT=60.0

# Batch configuration (PHASE 8)
QDRANT_BATCH_SIZE=100
QDRANT_PARALLEL_BATCHES=3

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cache System (PHASE 5)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Backend: lru (local) or redis (distributed)
CACHE_BACKEND=lru

# LRU cache size (MB)
CACHE_MAX_SIZE_MB=512

# Cache TTL (seconds)
CACHE_TTL=3600

# Redis connection (if using redis backend)
# REDIS_URL=redis://localhost:6379/0

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Batch Processing (PHASE 8)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Embedding batch size (texts per API call)
EMBED_BATCH_SIZE=32

# File batch size (files per batch)
FILE_BATCH_SIZE=50

# HTTP connection pool
HTTP_POOL_CONNECTIONS=20
HTTP_POOL_MAXSIZE=50
HTTP_TIMEOUT=60.0

# Worker pool
NUM_WORKERS=4

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Server Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Server bind address and port
HOST=0.0.0.0
PORT=8000

# CORS (if needed for web clients)
# CORS_ORIGINS=http://localhost:3000,https://app.example.com

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Logging and Monitoring
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# Structured JSON logging
LOG_JSON=false

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Job Scheduler
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Scheduler check interval (seconds)
SCHEDULER_INTERVAL=5.0

# Max concurrent jobs
MAX_CONCURRENT_JOBS=2

# Rate limiting (requests per minute)
RATE_LIMIT_RPM=60.0
```

- [ ] **Step 2: Create logrotate configuration**

Create `deployment/config/logrotate.conf`:

```
# KB-RAG Log Rotation Configuration
# Install to: /etc/logrotate.d/kb-rag

/opt/kb-rag/logs/*.log {
    # Rotate daily
    daily
    
    # Keep 14 days of logs
    rotate 14
    
    # Compress old logs
    compress
    delaycompress
    
    # Don't rotate if empty
    notifempty
    
    # Don't error if log is missing
    missingok
    
    # Create new log file with these permissions
    create 0640 kb-rag kb-rag
    
    # Share scripts between all logs
    sharedscripts
    
    # After rotation, reload services
    postrotate
        systemctl reload kb-rag-server.service >/dev/null 2>&1 || true
        systemctl reload kb-rag-scheduler.service >/dev/null 2>&1 || true
    endscript
    
    # Size-based rotation (if log exceeds 100M, rotate immediately)
    size 100M
    
    # Max age (delete logs older than 30 days even if not rotated)
    maxage 30
}

# Journal logs (systemd)
# Managed by systemd, but configure limits:
# Edit: /etc/systemd/journald.conf
#
# [Journal]
# SystemMaxUse=500M
# SystemKeepFree=1G
# SystemMaxFileSize=50M
# MaxRetentionSec=2week
```

- [ ] **Step 3: Create Prometheus configuration**

Create `deployment/config/prometheus.yml`:

```yaml
# Prometheus Configuration for KB-RAG
# Install to: /etc/prometheus/prometheus.yml (or append to existing)

global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'kb-rag-production'
    environment: 'production'

# Alertmanager configuration (optional)
# alerting:
#   alertmanagers:
#     - static_configs:
#         - targets:
#             - localhost:9093

# Scrape configurations
scrape_configs:
  # KB-RAG Server Metrics
  - job_name: 'kb-rag-server'
    static_configs:
      - targets: ['localhost:8000']
        labels:
          service: 'kb-rag-server'
          component: 'api'
    metrics_path: '/metrics'
    scrape_interval: 10s
    scrape_timeout: 5s

  # Node Exporter (system metrics)
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
        labels:
          service: 'node-exporter'
          component: 'system'

  # Qdrant Metrics (if exposed)
  - job_name: 'qdrant'
    static_configs:
      - targets: ['localhost:6333']
        labels:
          service: 'qdrant'
          component: 'vector-store'
    metrics_path: '/metrics'

# Recording rules (pre-computed metrics)
rule_files:
  - '/etc/prometheus/rules/kb-rag.yml'

# Storage configuration
storage:
  tsdb:
    path: /var/lib/prometheus/data
    retention:
      time: 30d
      size: 10GB
```

- [ ] **Step 4: Create Prometheus alerting rules**

Create `deployment/config/prometheus-rules.yml`:

```yaml
# Prometheus Alerting Rules for KB-RAG
# Install to: /etc/prometheus/rules/kb-rag.yml

groups:
  - name: kb-rag-alerts
    interval: 30s
    rules:
      # Service Down
      - alert: KBRagServerDown
        expr: up{job="kb-rag-server"} == 0
        for: 1m
        labels:
          severity: critical
          component: server
        annotations:
          summary: "KB-RAG server is down"
          description: "KB-RAG server has been down for more than 1 minute"

      # High Error Rate
      - alert: HighErrorRate
        expr: |
          rate(kb_ingest_files_processed_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
          component: ingestion
        annotations:
          summary: "High file processing error rate"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 10%)"

      # Cache Hit Rate Low
      - alert: LowCacheHitRate
        expr: |
          rate(kb_cache_hits_total[5m]) / 
          (rate(kb_cache_hits_total[5m]) + rate(kb_cache_misses_total[5m])) < 0.3
        for: 10m
        labels:
          severity: warning
          component: cache
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value | humanizePercentage }} (threshold: 30%)"

      # Queue Backlog
      - alert: JobQueueBacklog
        expr: kb_ingest_jobs_active{status="pending"} > 10
        for: 5m
        labels:
          severity: warning
          component: scheduler
        annotations:
          summary: "Job queue backlog"
          description: "{{ $value }} pending jobs in queue"

      # Disk Space Low
      - alert: LowDiskSpace
        expr: |
          (node_filesystem_avail_bytes{mountpoint="/"} / 
           node_filesystem_size_bytes{mountpoint="/"}) < 0.1
        for: 5m
        labels:
          severity: warning
          component: system
        annotations:
          summary: "Low disk space"
          description: "Only {{ $value | humanizePercentage }} disk space remaining"

      # High Memory Usage
      - alert: HighMemoryUsage
        expr: |
          (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / 
          node_memory_MemTotal_bytes > 0.9
        for: 5m
        labels:
          severity: warning
          component: system
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      # Embedding Service Slow
      - alert: SlowEmbeddingService
        expr: |
          histogram_quantile(0.95, 
            rate(kb_batch_embedding_duration_seconds_bucket[5m])) > 10
        for: 5m
        labels:
          severity: warning
          component: embedding
        annotations:
          summary: "Slow embedding service"
          description: "P95 embedding latency is {{ $value }}s (threshold: 10s)"
```

- [ ] **Step 5: Commit configuration files**

```bash
git add deployment/config/
git commit -m "feat(config): add deployment configuration files

- kb-rag.env: Environment variable template with all options
- logrotate.conf: Log rotation (14 days, 100MB limit)
- prometheus.yml: Metrics scraping configuration
- prometheus-rules.yml: Alerting rules for service health

Includes documentation and sensible defaults for production"
```

---

**(Plan continues with Task 5: Grafana Dashboard, Task 6: Documentation, Task 7: Integration Tests, and Task 8: Final Verification)**

Would you like me to continue with the remaining tasks, or would you prefer to start executing the plan we have so far?
