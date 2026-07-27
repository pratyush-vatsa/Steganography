#!/usr/bin/env bash
set -e

export STEGO_BASE_DIR="${STEGO_BASE_DIR:-/tmp/stego-data}"
mkdir -p "$STEGO_BASE_DIR"

# Run gunicorn binding to the platform-provided $PORT (defaults to 5000).
# --workers 1: each worker is a separate process with its own full copy of
# numpy/scipy/matplotlib/PIL loaded in memory (~150-250MB baseline just for
# imports, before processing anything). On a memory-constrained host (e.g.
# a 1GB free-tier VM), 2 workers means 2x that baseline PLUS the risk of
# two memory-heavy hide/extract requests running concurrently and combining
# to exceed available RAM, which is exactly what triggers an OOM kill mid-
# request (visible as "upstream prematurely closed connection" in nginx's
# error log, and "The kernel OOM killer killed some processes" via
# `journalctl -u stego`). If you're deploying on a host with 2GB+ RAM,
# --workers 2 is fine and gives real concurrency; on 1GB, keep this at 1.
# --timeout 120: large cover images (20-30MP) can take 15-25s to process
# (mostly SSIM quality-metric calculation), comfortably under gunicorn's
# default 30s worker timeout margin but better to give real headroom.
exec gunicorn run:app --workers 1 --timeout 120 --bind 0.0.0.0:"${PORT:-5000}"
