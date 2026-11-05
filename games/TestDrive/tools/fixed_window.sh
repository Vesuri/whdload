#!/bin/bash
# Default: retained phase-4 baseline first attract-race window. ANCHOR retains root diagnostics.
set -euo pipefail
. "$(dirname "$0")/env.sh"
[ "$#" -ge 1 ] || { echo 'Usage: fixed_window.sh OUT [SLAVE]' >&2; exit 2; }
if [ -z "${ANCHOR:-}" ]; then
  export SLAVE="${2:-${SLAVE:-$HARNESS_ROOT/tmp/phase4/base-a500-1/slave.slave}}"
  export WHD_ARGS="${WHD_ARGS:-CUSTOM3=1}"
  args=("$1" --fields "${FIELDS:-100}")
  [ "${SWAP_ONLY:-0}" != 1 ] || args+=(--swap-only)
  [ -z "${H4_BASE:-}" ] || args+=(--h4 "$H4_BASE")
  exec python3 "$HARNESS_ROOT/tools/race_capture.py" "${args[@]}"
fi
args=(fixed "$1" --anchor "$ANCHOR" --fields "${FIELDS:-5}" --state-fields "${STATE_FIELDS:-0}" --skip-fields "${SKIP_FIELDS:-0}" --timeout "${SERVE_WAIT:-300}")
[ "$#" -lt 2 ] || args+=(--slave "$2")
[ "${STATE_ONLY:-0}" != 1 ] || args+=(--state-only)
[ -z "${SWAP_OFFSET:-}" ] || args+=(--swap-offset "$SWAP_OFFSET")
[ "${SWAP_ONLY:-0}" != 1 ] || args+=(--swap-only)
[ "${WATCH_STATE:-0}" != 1 ] || args+=(--watch-state)
exec python3 "$HARNESS_ROOT/tools/capture.py" "${args[@]}"
