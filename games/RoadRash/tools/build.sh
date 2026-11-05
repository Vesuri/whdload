#!/usr/bin/env bash
# The harness's builds of src/ into tmp/build (make slave builds the release, tmp/build/release/):
#   tools/build.sh                 RoadRash.slave (normal) and the RoadRash-verify*.slave builds
#   CHECK=1 tools/build.sh         also compare the normal build with the shipped v2.0 slave
# Extra vasm defines for the VERIFY build: VERIFY_DEFINES="-DFOO=1". RR_SOURCE selects another
# source directory, RR_BUILD_OUT another output directory.
# The release source has no VERIFY instrumentation: the VERIFY builds need the development
# branch's source (docs/development.md), which RR_SOURCE can point at.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/../../common/env.sh"
GAME_SOURCE="${RR_SOURCE:-$ROOT/src}"
GAME="${GAME_PATH:-$ROOT/tmp/game/RoadRash}"
VASM="${VASM:-$HOME/.local/vasmm68k_mot}"
WHD="$AMIGA_SHARE/WHDLoad"
OUT="${RR_BUILD_OUT:-$ROOT/tmp/build}"
mkdir -p "$OUT"
build() {  # name defines...
  local name="$1"; shift
  (cd "$GAME_SOURCE" && "$VASM" -quiet "$@" -devpac -nosym -Fhunkexe -pic \
    -I"$WHD/Include" -I"$WHD/Src" -I"$AMIGA_SHARE/ndk/Include_I" -I. \
    -L "$OUT/$name.lst" -o "$OUT/$name.slave" RoadRashHD.s)
}
rm -f "$OUT"/RoadRash*.slave
build RoadRash
# shellcheck disable=SC2086
build RoadRash-verify -DVERIFY ${VERIFY_DEFINES:-}
build RoadRash-verify-hash -DVERIFY -DVERIFY_HASH_FIELD=590
build RoadRash-verify-mmu -DVERIFY -DVERIFY_MMU
if [ "${CHECK:-0}" = 1 ]; then
  cmp "$OUT/RoadRash.slave" "$GAME/RoadRash.slave"
  echo "normal build equals the shipped slave"
fi
ls -l "$OUT"/RoadRash*.slave
