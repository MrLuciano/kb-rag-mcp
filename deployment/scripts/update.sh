#!/bin/bash
#
# KB-RAG Update Script
#
# Updates KB-RAG to a new version.
#
# Usage:
#   sudo ./update.sh [--version TAG]
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
VERSION="${1:-main}"

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

check_root

log_info "KB-RAG Update Script"
log_info "Target version: $VERSION"
echo

# Create backup
log_info "Creating backup before update..."
BACKUP_FILE="/tmp/kb-rag-backup-pre-update-$(date +%s).tar.gz"
"$INSTALL_DIR/deployment/scripts/backup.sh" "$BACKUP_FILE"
log_info "Backup saved: $BACKUP_FILE"

# Stop services
log_info "Stopping services..."
systemctl stop kb-rag.target

# Update code
log_info "Updating application code..."
cd "$INSTALL_DIR"

if [[ -d .git ]]; then
    # Git repository - pull latest
    sudo -u "$KB_USER" git fetch origin
    sudo -u "$KB_USER" git checkout "$VERSION"
    sudo -u "$KB_USER" git pull origin "$VERSION"
else
    log_error "Not a git repository. Manual update required."
    exit 1
fi

# Update dependencies
log_info "Updating dependencies..."
source "$INSTALL_DIR/venv/bin/activate"
pip install --upgrade pip wheel setuptools
pip-sync requirements.txt
deactivate

# Update systemd files if changed
if [[ -f deployment/systemd/kb-rag-server.service ]]; then
    log_info "Updating systemd services..."
    cp deployment/systemd/*.service /etc/systemd/system/
    cp deployment/systemd/*.target /etc/systemd/system/
    systemctl daemon-reload
fi

# Set permissions
log_info "Setting permissions..."
chown -R "$KB_USER:$KB_USER" "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR/deployment/scripts"

# Start services
log_info "Starting services..."
systemctl start kb-rag.target

# Wait and check
sleep 5
if systemctl is-active --quiet kb-rag-server.service; then
    log_info "✓ Update successful"
else
    log_error "✗ Services failed to start"
    log_error "Rolling back from backup: $BACKUP_FILE"
    "$INSTALL_DIR/deployment/scripts/restore.sh" "$BACKUP_FILE"
    exit 1
fi

# Show status
echo
log_info "Update complete!"
echo
log_info "New version:"
cd "$INSTALL_DIR"
git describe --tags 2>/dev/null || git rev-parse --short HEAD

echo
log_info "Service status:"
systemctl status kb-rag.target --no-pager
