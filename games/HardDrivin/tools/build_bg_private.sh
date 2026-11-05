#!/bin/bash
# Build the private background-prototype source copy in tmp/s5-bg-source (step 5), as
# tools/build.sh builds src/: OUTPUT_SLAVE=... tools/build_bg_private.sh [vasm flags...]
set -eu
GAME_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$GAME_ROOT/tools/env.sh"
mkdir -p "$GAME_ROOT/tmp/build"
cd "$GAME_ROOT/tmp/s5-bg-source"
"$VASM" -m68000 -pic -x -devpac -Fhunkexe -nosym \
  -I"$AMIGA_INCLUDE" -I"$WHDLOAD/Include" -I"$WHDLOAD/Src/sources" -I"$NDK" \
  -o "${OUTPUT_SLAVE:-$GAME_ROOT/tmp/build/HardDrivin.Slave}" "$@" HardDrivinHD.s
