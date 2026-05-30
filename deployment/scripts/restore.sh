#!/bin/bash
#
# KB-RAG Restore Script
#
# Restores KB-RAG data and configuration from a backup.
#
# Usage:
#   sudo ./restore.sh /path/to/backup.tar.gz
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
INSTALL_DIR="${INSTALL_DIR:-/opt/kb-rag}"
BACKUP_FILE="${1:-}"

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

if [[ -z "$BACKUP_FILE" ]]; then
    log_error "Usage: $0 /path/to/backup.tar.gz"
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

check_root

log_info "Restoring from: $BACKUP_FILE"
echo

# Stop services
log_info "Stopping services..."
systemctl stop kb-rag.target || true

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Extract backup
log_info "Extracting backup..."
tar xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# Show manifest
if [[ -f "$TEMP_DIR/MANIFEST.txt" ]]; then
    cat "$TEMP_DIR/MANIFEST.txt"
    echo
fi

# Backup current data (safety)
if [[ -d "$INSTALL_DIR/data" ]]; then
    log_warn "Creating safety backup of current data..."
    SAFETY_BACKUP="/tmp/kb-rag-data-before-restore-$(date +%s).tar.gz"
    tar czf "$SAFETY_BACKUP" -C "$INSTALL_DIR" data
    log_info "Safety backup: $SAFETY_BACKUP"
fi

# Restore data
if [[ -d "$TEMP_DIR/data" ]]; then
    log_info "Restoring data..."
    rm -rf "$INSTALL_DIR/data"
    cp -r "$TEMP_DIR/data" "$INSTALL_DIR/"
fi

# Restore configuration
if [[ -d "$TEMP_DIR/config" ]]; then
    log_info "Restoring configuration..."
    cp -r "$TEMP_DIR/config"/* "$INSTALL_DIR/config/" || true
fi

# Set permissions
log_info "Setting permissions..."
chown -R kb-rag:kb-rag "$INSTALL_DIR/data"
chown -R kb-rag:kb-rag "$INSTALL_DIR/config"

# Start services
log_info "Starting services..."
systemctl start kb-rag.target

# Wait and check
sleep 5
if systemctl is-active --quiet kb-rag-server.service; then
    log_info "✓ Services restored successfully"
else
    log_error "✗ Services failed to start, check logs"
    systemctl status kb-rag-server.service --no-pager
    exit 1
fi

log_info "Restore complete!"
