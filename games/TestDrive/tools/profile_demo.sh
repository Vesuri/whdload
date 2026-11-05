#!/bin/bash
set -euo pipefail
. "$(dirname "$0")/env.sh"
exec python3 "$HARNESS_ROOT/tools/capture.py" demo "${1:-$HARNESS_ROOT/tmp/prof/demo-$(date +%Y%m%d-%H%M%S)}" --fields "${FIELDS:-5}" --timeout "${DEMO_TIMEOUT:-300}"
