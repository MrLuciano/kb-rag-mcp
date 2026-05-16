#!/bin/bash
#
# KB-RAG Backup Script
#
# Creates a backup of KB-RAG data, configuration, and databases.
#
# Usage:
#   ./backup.sh [--output /path/to/backup.tar.gz]
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
INSTALL_DIR="${INSTALL_DIR:-/opt/kb-rag}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT="${1:-/tmp/kb-rag-backup-${TIMESTAMP}.tar.gz}"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

log_info "Creating backup..."

# Backup databases
log_info "Backing up databases..."
cp -r "$INSTALL_DIR/data" "$TEMP_DIR/" || true

# Backup configuration
log_info "Backing up configuration..."
cp -r "$INSTALL_DIR/config" "$TEMP_DIR/" || true

# Backup logs (last 7 days)
log_info "Backing up recent logs..."
mkdir -p "$TEMP_DIR/logs"
find "$INSTALL_DIR/logs" -name "*.log" -mtime -7 \
    -exec cp {} "$TEMP_DIR/logs/" \; || true

# Create manifest
cat > "$TEMP_DIR/MANIFEST.txt" <<EOF
KB-RAG Backup Manifest
Created: $TIMESTAMP
Source: $INSTALL_DIR

Contents:
- data/           (databases and indexed data)
- config/         (configuration files)
- logs/           (recent logs, last 7 days)

To restore:
  sudo ./restore.sh /path/to/backup.tar.gz
EOF

# Create tarball
log_info "Creating archive..."
tar czf "$OUTPUT" -C "$TEMP_DIR" .

# Get size
SIZE=$(du -h "$OUTPUT" | cut -f1)

log_info "Backup complete: $OUTPUT ($SIZE)"
echo
echo "To restore this backup:"
echo "  sudo ./restore.sh $OUTPUT"
