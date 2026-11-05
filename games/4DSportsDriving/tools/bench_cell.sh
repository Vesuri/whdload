#!/usr/bin/env bash
# SLAVE CELL OUTPUT; current baseline route uses VERIFY keyboard instrumentation.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 tools/bench_cell.py "$@"
