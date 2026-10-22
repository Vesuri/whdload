#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
. amiga/env.sh
export NDK_ASM="${NDK_ASM:-$AMIGA_SHARE/ndk/Include_I}"
python3 tools/slave_toolchain.py
python3 tools/slave_inputs.py
OUT="${OUT:-tmp/build}"
mkdir -p "$OUT" tmp/slave/include/lvo
for lib in dos exec graphics expansion; do
  printf '        INCLUDE "lvo/%s_lib.i"\n' "$lib" > "tmp/slave/include/lvo/$lib.i"
done
"$VASM" -m68000 -no-opt -pic -x -devpac -Fhunkexe -nosym \
  -Itmp/slave/include -I"$NDK_ASM" -I"$WHDLOAD/Include" -I"$NDK" -I"$WHDLOAD/Src/sources" \
  -o "$OUT/F1GP.Slave" -L "$OUT/F1GP.lst" whdload/F1GP.s
