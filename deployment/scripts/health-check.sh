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

check_health() {
    local url="http://$HOST:$PORT/alive"
    
    if response=$(curl -sf --max-time "$TIMEOUT" "$url" 2>/dev/null); then
        if echo "$response" | grep -q '"alive":\s*true'; then
            echo "✓ Health server is alive"
            return 0
        else
            echo "✗ Health server returned unexpected response"
            return 1
        fi
    else
        echo "✗ Health server is not responding"
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
        exit $?
        ;;
    health)
        check_health
        exit $?
        ;;
    scheduler)
        check_scheduler
        exit $?
        ;;
    all)
        failed=0
        check_server || failed=1
        check_health || failed=1
        check_scheduler || failed=1
        exit $failed
        ;;
    *)
        echo "Usage: $0 [server|health|scheduler|all]"
        exit 2
        ;;
esac
