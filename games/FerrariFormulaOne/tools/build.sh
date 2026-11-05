#!/usr/bin/env bash
set -euo pipefail
HARNESS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$HARNESS_ROOT/../../common/env.sh"
MODE="${1:-release}"
case "$MODE" in imported|release|verify) ;; *) echo 'Expected imported, release or verify' >&2; exit 2;; esac
BUILD="$HARNESS_ROOT/tmp/build/$MODE"
mkdir -p "$BUILD"
ln -sfn "$WHDLOAD/Include" "$BUILD/SOURCES:Include"
ln -sfn "$WHDLOAD/Src/sources/whdload" "$BUILD/Sources:whdload"
export HARNESS_ROOT BUILD MODE
python3 - <<'PY'
import os, pathlib, hashlib, json
src=pathlib.Path(os.environ['HARNESS_ROOT'])/'src/FerrariFormulaOne_WHD.s'
data=src.read_bytes()
# Published BOOTDOS conditional has no terminator; close it in the build copy.
data += b'\n\tENDC ; close published BOOTDOS conditional for vasm\n'
if os.environ['MODE'] != 'imported':
    assert data.count(b'\nDEBUG\n') == 1
    data=data.replace(b'\nDEBUG\n',b'\n;DEBUG ; local release build\n')
p=pathlib.Path(os.environ['BUILD'])
(p/'FerrariFormulaOne_WHD.s').write_bytes(data)
(p/'source.json').write_text(json.dumps({'authoritative_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'mode':os.environ['MODE'],'staged_sha256':hashlib.sha256(data).hexdigest()},indent=2)+'\n')
PY
mkdir -p "$BUILD/lvo"
for lib in dos exec graphics expansion; do
  printf ' IFND FF1_LVO_%s\nFF1_LVO_%s SET 1\n INCLUDE "lvo/%s_lib.i"\n ENDC\n' "$lib" "$lib" "$lib" > "$BUILD/lvo/$lib.i"
done
cd "$BUILD"
FLAGS=()
[ "$MODE" = verify ] && FLAGS+=(-DVERIFY=1)
"$VASM" "${FLAGS[@]}" -m68000 -pic -x -devpac -Fhunkexe -nosym \
 -I"$BUILD" -I"$WHDLOAD/Include" -I"$WHDLOAD/Src/sources" -I"$NDK" \
 -L build.list -o FerrariFormulaOne.slave FerrariFormulaOne_WHD.s > build.log 2>&1
shasum -a 256 FerrariFormulaOne.slave
