#!/usr/bin/env bash
# Serial native/SIM60 rate matrix; results and emulator artifacts stay in tmp/.
set -euo pipefail
cd "$(dirname "$0")/.."
. amiga/env.sh
exec python3 tools/rate_matrix.py "$@"
