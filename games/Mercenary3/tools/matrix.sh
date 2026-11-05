#!/bin/bash
# Sequential machine matrix; generated results must live under tmp/.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
. "$ROOT/amiga/env.sh"
exec python3 "$ROOT/tools/matrix.py" "$@"
