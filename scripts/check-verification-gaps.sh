#!/usr/bin/env bash
# VERBACK-04: Gap detection script — lists phases missing VERIFICATION.md
set -euo pipefail

PHASES_DIR=".planning/phases"
FOUND=0

for dir in "$PHASES_DIR"/*/; do
    phase=$(basename "$dir")
    if ! ls "$dir"*VERIFICATION* 1>/dev/null 2>&1; then
        echo "MISSING: $phase"
        FOUND=$((FOUND + 1))
    fi
done

if [ "$FOUND" -eq 0 ]; then
    echo "All phases have VERIFICATION.md — no gaps detected."
else
    echo ""
    echo "---"
    echo "$FOUND phase(s) missing VERIFICATION.md"
fi
