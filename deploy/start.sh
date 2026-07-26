#!/usr/bin/env bash
set -e

export STEGO_BASE_DIR="${STEGO_BASE_DIR:-/tmp/stego-data}"
mkdir -p "$STEGO_BASE_DIR"

# Run gunicorn binding to the platform-provided $PORT (defaults to 5000).
# --timeout 120: large cover images (20-30MP) can take 15-25s to process
# (mostly SSIM quality-metric calculation), comfortably under gunicorn's
# default 30s worker timeout margin but better to give real headroom.
exec gunicorn run:app --workers 2 --timeout 120 --bind 0.0.0.0:"${PORT:-5000}"
