#!/bin/bash
# The colour census's inputs (resolution plan step 3), for tools/colours.py.
#
#   tools/census.sh [OUT]     OUT default tmp/colours
#
# One deterministic boot (WARP=1 DETERMINISTIC=1 JOY0=none; CUSTOM1=7: unlimited energy
# and shots, F1 skips the level) on the game's setup: in level 1 `ab3d.py tables` dumps the
# loaded walls and floor texture into OUT/tables; then at each of the 16 levels' starts
# `ab3d.py grab` keeps every frame shown over 360 fields of turning and walking, then 720 of
# walking and turning with the gun firing (aliens, shots, explosions), all into
# OUT/frames/L.bin, and F1 goes on.
set -eu
game=$(cd "$(dirname "$0")/.." && pwd)
cd "$game"
. ../../common/env.sh
out=${1:-tmp/colours}
mkdir -p "$out/frames"
out=$(cd "$out" && pwd)
export INSTANCE=census WARP=1 WINDOW=none DETERMINISTIC=1 JOY0=none WHD_ARGS='CUSTOM1=7'
explore='60 mx 40; 60 my -12; 60 mx 40; 60 my -12; 60 mx 40; 60 my -12'
fight='60 mx 40 fire; 120 my -12 fire; 60 mx -40 fire; 120 my -12 fire; 60 mx 40 fire; 120 my -12 fire; 60 mx 40 fire; 120 my -12 fire'

ab3d() { python3 tools/ab3d.py "$@"; }

trap 'ab3d quit > /dev/null 2>&1 || true' EXIT
python3 tools/ab3d.py serve > "$out/serve.log" 2>&1 &
i=0
until [ -S "tmp/run/$INSTANCE/.run/ab3d.sock" ] && grep -q '^serving' "$out/serve.log"; do
  i=$((i + 1))
  [ $i -lt 120 ] || { echo 'server did not start' >&2; cat "$out/serve.log" >&2; exit 1; }
  sleep 0.5
done
ab3d wait 20 > /dev/null
ab3d level | tee "$out/log.txt"
ab3d tables "$out/tables" | tee -a "$out/log.txt"
rm -f "$out"/frames/*.bin
for level in a b c d e f g h i j k l m n o p; do
  ab3d grab 360 "$out/frames/$level.bin" "$explore" | tee -a "$out/log.txt"
  ab3d grab 720 "$out/frames/$level.bin" "$fight" | tee -a "$out/log.txt"
  [ $level = p ] || ab3d next | tee -a "$out/log.txt"
done
