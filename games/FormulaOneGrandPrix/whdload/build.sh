#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
. amiga/env.sh
export NDK_ASM="${NDK_ASM:-$AMIGA_SHARE/ndk/Include_I}"
python3 tools/slave_toolchain.py
python3 tools/slave_inputs.py
python3 tools/e2_tables.py > /dev/null
python3 tools/e4_tables.py > /dev/null
python3 tools/f5_sites.py > /dev/null
BUILD="${BUILD:-release}"
case "$BUILD" in
  release) defines=(-DDEVELOPER=0 -DVERIFY=0) ;;
  developer) defines=(-DDEVELOPER=1) ;;
  verify) defines=(-DDEVELOPER=1 -DVERIFY=1) ;;
  *) echo "Unknown BUILD: $BUILD" >&2; exit 1 ;;
esac
OUT="${OUT:-tmp/build}"
python3 - "$OUT" <<'PYOUT'
from pathlib import Path
import sys
out = Path(sys.argv[1]).resolve()
if not out.is_relative_to(Path('tmp').resolve()):
    sys.exit('Slave outputs must stay under the project tmp/ directory')
PYOUT
if [ "${CLEAN:-0}" = 1 ]; then
  rm -f "$OUT/F1GP.Slave" "$OUT/F1GP.lst" "$OUT/build.json"
  exit 0
fi
mkdir -p "$OUT" tmp/slave/include/lvo
for lib in dos exec graphics expansion; do
  printf '        INCLUDE "lvo/%s_lib.i"\n' "$lib" > "tmp/slave/include/lvo/$lib.i"
done
"$VASM" "${defines[@]}" -m68000 -no-opt -pic -x -devpac -Fhunkexe -nosym \
  -Itmp/slave/include -I"$NDK_ASM" -I"$WHDLOAD/Include" -I"$NDK" -I"$WHDLOAD/Src/sources" \
  -o "$OUT/F1GP.Slave" -L "$OUT/F1GP.lst" whdload/F1GP.s

python3 - "$OUT" "$BUILD" <<'PYMETA'
import hashlib, json, sys
from pathlib import Path
out = Path(sys.argv[1])
meta = dict(build=sys.argv[2], slave_sha256=hashlib.sha256((out/'F1GP.Slave').read_bytes()).hexdigest(),
            source_sha256=hashlib.sha256(Path('whdload/F1GP.s').read_bytes()).hexdigest())
(out/'build.json').write_text(json.dumps(meta, indent=2)+'\n')
PYMETA
