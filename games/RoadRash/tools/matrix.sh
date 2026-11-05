#!/usr/bin/env bash
# Diagnostic matrix, all CPU cells plus MMU functional boots.
# OUT chooses a fresh result directory; --normal selects uninstrumented timing cells.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 tools/matrix_a.py "${OUT:-tmp/rate/$(date -u +%Y%m%dT%H%M%SZ)}" "$@"
