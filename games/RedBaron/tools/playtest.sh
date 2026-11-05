#!/usr/bin/env bash
# D5 player candidate: real speed, sound, physical keyboard, no VERIFY fixtures.
set -euo pipefail
GAME_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$GAME_ROOT/../../common/env.sh"
cd "$GAME_ROOT"
exec python3 -B tools/playtest.py "$@"
