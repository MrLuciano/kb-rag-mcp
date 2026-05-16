#!/bin/bash
#
# KB-RAG Uninstall Script
#
# Removes KB-RAG system and optionally data.
#
# Usage:
#   sudo ./uninstall.sh [--keep-data]
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
INSTALL_DIR="${INSTALL_DIR:-/opt/kb-rag}"
KB_USER="kb-rag"
KEEP_DATA=false

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

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --keep-data)
            KEEP_DATA=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

check_root

log_warn "This will remove KB-RAG from your system"
if [[ "$KEEP_DATA" == "false" ]]; then
    log_warn "Data will be DELETED"
else
    log_info "Data will be preserved"
fi
echo
read -p "Continue? (yes/no): " confirm

if [[ "$confirm" != "yes" ]]; then
    log_info "Aborted"
    exit 0
fi

# Stop services
log_info "Stopping services..."
systemctl stop kb-rag.target || true

# Disable services
log_info "Disabling services..."
systemctl disable kb-rag-server.service || true
systemctl disable kb-rag-health.service || true
systemctl disable kb-rag-scheduler.service || true
systemctl disable kb-rag.target || true

# Remove service files
log_info "Removing systemd services..."
rm -f /etc/systemd/system/kb-rag-*.service
rm -f /etc/systemd/system/kb-rag.target
systemctl daemon-reload

# Remove logrotate config
log_info "Removing logrotate config..."
rm -f /etc/logrotate.d/kb-rag

# Backup data if requested
if [[ "$KEEP_DATA" == "true" ]] && [[ -d "$INSTALL_DIR/data" ]]; then
    BACKUP_FILE="/tmp/kb-rag-data-backup-$(date +%s).tar.gz"
    log_info "Backing up data to: $BACKUP_FILE"
    tar czf "$BACKUP_FILE" -C "$INSTALL_DIR" data
    log_info "Data backup saved: $BACKUP_FILE"
fi

# Remove installation directory
log_info "Removing installation directory..."
if [[ "$KEEP_DATA" == "true" ]]; then
    # Keep data, remove everything else
    rm -rf "$INSTALL_DIR/server"
    rm -rf "$INSTALL_DIR/ingest"
    rm -rf "$INSTALL_DIR/observability"
    rm -rf "$INSTALL_DIR/config"
    rm -rf "$INSTALL_DIR/deployment"
    rm -rf "$INSTALL_DIR/venv"
    rm -rf "$INSTALL_DIR/logs"
    log_info "Kept data directory: $INSTALL_DIR/data"
else
    # Remove everything
    rm -rf "$INSTALL_DIR"
    log_info "Removed: $INSTALL_DIR"
fi

# Remove user
log_info "Removing user $KB_USER..."
if id "$KB_USER" &>/dev/null; then
    userdel "$KB_USER" || log_warn "Failed to remove user"
fi

log_info "Uninstall complete"

if [[ "$KEEP_DATA" == "true" ]]; then
    echo
    log_info "Data preserved at: $INSTALL_DIR/data"
    log_info "Or backed up to: $BACKUP_FILE"
fi
