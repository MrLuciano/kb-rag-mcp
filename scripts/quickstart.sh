#!/usr/bin/env bash
# quickstart.sh — zero-to-running setup for kb-rag-mcp
# Usage: bash scripts/quickstart.sh [--docs /path/to/docs]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_PATH=""

# ── Parse args ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --docs) DOCS_PATH="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[kb-rag]${NC} $*"; }
warn()  { echo -e "${YELLOW}[kb-rag]${NC} $*"; }
error() { echo -e "${RED}[kb-rag]${NC} $*" >&2; exit 1; }

# ── 1. Prerequisites ─────────────────────────────────────────────────────────
info "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || error "python3 not found — install Python 3.11+"
command -v docker  >/dev/null 2>&1 || error "docker not found — install Docker"
command -v docker compose >/dev/null 2>&1 || \
    command -v docker-compose >/dev/null 2>&1 || \
    error "docker compose not found"

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
[[ "$(echo "$PY_VER 3.11" | awk '{print ($1 >= $2)}')" == "1" ]] \
    || error "Python 3.11+ required (found $PY_VER)"

# ── 2. .env ──────────────────────────────────────────────────────────────────
cd "$REPO_ROOT"
if [[ ! -f .env ]]; then
    info "Creating .env from template..."
    cp config/.env.template .env
    if [[ -n "$DOCS_PATH" ]]; then
        sed -i "s|DOCS_PATH=.*|DOCS_PATH=$DOCS_PATH|" .env
        sed -i "s|WATCH_PATH=.*|WATCH_PATH=$DOCS_PATH|" .env
    fi
    warn ".env created — edit it to set EMBED_URL, EMBED_MODEL, and DOCS_PATH before ingesting."
else
    info ".env already exists — skipping."
fi

# ── 3. Python virtual environment ────────────────────────────────────────────
if [[ ! -d .venv ]]; then
    info "Creating virtual environment..."
    python3 -m venv .venv
fi
info "Installing Python dependencies..."
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet --no-deps -e .

# ── 4. Start Qdrant ──────────────────────────────────────────────────────────
info "Starting Qdrant with Docker Compose..."
if command -v docker compose >/dev/null 2>&1; then
    docker compose up -d qdrant
else
    docker-compose up -d qdrant
fi

# Wait for Qdrant to be ready (up to 30s)
info "Waiting for Qdrant to be ready..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:6333/healthz >/dev/null 2>&1; then
        info "Qdrant is up."
        break
    fi
    sleep 1
    if [[ $i -eq 30 ]]; then
        error "Qdrant did not become ready in 30s. Check: docker compose logs qdrant"
    fi
done

# ── 5. Start MCP server ──────────────────────────────────────────────────────
info "Starting kb-rag-mcp server..."
MCP_LOG=logs/kb-rag-mcp.log
mkdir -p logs
nohup python -m kb_server.server >"$MCP_LOG" 2>&1 &
MCP_PID=$!
echo "$MCP_PID" > /tmp/kb-rag-mcp.pid
info "MCP server started (PID $MCP_PID). Logs: $MCP_LOG"

# Wait for health endpoint
info "Waiting for health endpoint..."
HEALTH_PORT="${HEALTH_PORT:-8080}"
for i in $(seq 1 20); do
    if curl -sf "http://localhost:${HEALTH_PORT}/health" >/dev/null 2>&1; then
        info "Health endpoint is up."
        break
    fi
    sleep 1
    if [[ $i -eq 20 ]]; then
        warn "Health endpoint not responding — server may still be starting. Check $MCP_LOG"
    fi
done

# ── 6. Ingest docs (optional) ────────────────────────────────────────────────
if [[ -n "$DOCS_PATH" ]]; then
    info "Ingesting documents from $DOCS_PATH..."
    python ingest/ingest.py --docs "$DOCS_PATH" || warn "Ingest completed with warnings — check output above."
    info "Ingest complete."
fi

# ── 7. Summary ───────────────────────────────────────────────────────────────
echo ""
info "=== Setup complete ==="
echo ""
echo "  Qdrant REST:   http://localhost:6333"
echo "  MCP server:    running (SSE on port 8000, health on port ${HEALTH_PORT:-8080})"
echo "  Logs:          $REPO_ROOT/$MCP_LOG"
echo ""
echo "  Add to your MCP client config (e.g. ~/.opencode/config.json):"
echo '  { "mcpServers": { "kb-rag": { "url": "http://localhost:8000/sse" } } }'
echo ""
if [[ -z "$DOCS_PATH" ]]; then
    warn "No --docs path given. Ingest your docs with:"
    echo "    source .venv/bin/activate && python ingest/ingest.py --docs /path/to/docs"
fi
