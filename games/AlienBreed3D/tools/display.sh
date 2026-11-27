#!/bin/bash
# Enhanced resolution's display skeleton against the original (resolution plan step 4).
#
#   tools/display.sh [OUT [SETUP]]     OUT default tmp/display, SETUP default game.conf's
#
# Two deterministic boots of the release slave on SETUP, the option off (the original's
# display; CUSTOM1=4: F1 ends the level) and then on (also CUSTOM5=1), each through the
# same scenes: level 1's start in the small view and full screen, the pause screen in both
# and the level's end (`ab3d.py end`: F1, then the last frame, once no frame has followed
# it for twice the frames' time). With the option on also a death in both views (level 2, the `fight` script until
# the energy is gone; level 1's aliens never get through) and level 2's end.
# Each scene keeps a screenshot (OUT/RUN/SCENE.png) and the frame on screen (SCENE.frame),
# ours also the area (OUT/ours/area.bin). Then `tools/display.py` checks each screenshot
# against its frame and each of ours against the original's but the deaths and level 2's
# end (game time follows the frame rate, so after a fight the runs no longer share a
# state). Exit status 1 when a check fails.
set -eu
game=$(cd "$(dirname "$0")/.." && pwd)
cd "$game"
. ../../common/env.sh
out=${1:-tmp/display}
[ -n "${2:-}" ] && export SETUP=$2
mkdir -p "$out"
out=$(cd "$out" && pwd)
export INSTANCE=${INSTANCE:-display} WARP=1 WINDOW=none DETERMINISTIC=1 JOY0=none
sock=tmp/run/$INSTANCE/.run/ab3d.sock

ab3d() { python3 tools/ab3d.py "$@"; }
scene() {   # scene NAME: the screenshot and the frame
  ab3d shot "$dir/$1.png" > /dev/null
  ab3d frame "$dir/$1.frame"
}

run() {     # run NAME WHD_ARGS
  dir=$out/$1
  mkdir -p "$dir"
  rm -f "$dir"/*.png "$dir"/*.frame "$dir"/*.alt "$sock"
  WHD_ARGS=$2 python3 tools/ab3d.py serve > "$dir/serve.log" 2>&1 &
  i=0
  until [ -S "$sock" ] && grep -q '^serving' "$dir/serve.log"; do
    i=$((i + 1))
    [ $i -lt 240 ] || { echo 'server did not start' >&2; cat "$dir/serve.log" >&2; exit 1; }
    sleep 0.5
  done
  ab3d wait 20 > /dev/null
  ab3d level
  case $2 in *CUSTOM5=1*) ab3d palette "$dir/area.bin" 1 ;; esac
  scene start-small
  ab3d full 1; ab3d play 20 > /dev/null; scene start-full
  ab3d pause on > /dev/null; scene pause-full
  ab3d pause off > /dev/null
  ab3d full 0; ab3d play 20 > /dev/null
  ab3d pause on > /dev/null; scene pause-small
  ab3d pause off > /dev/null
  ab3d end; scene end-small
  # the deaths and the end after them only with the option on (see above)
  case $2 in *CUSTOM5=1*) ;; *) ab3d quit > /dev/null; return ;; esac
  ab3d level
  ab3d full 1; ab3d die 20000; ab3d play 30 > /dev/null; scene die-full
  ab3d level
  ab3d full 0; ab3d die 20000; ab3d play 30 > /dev/null; scene die-small
  ab3d level
  ab3d full 1; ab3d play 20 > /dev/null
  ab3d end; scene end-full
  ab3d quit > /dev/null
}

trap 'ab3d quit > /dev/null 2>&1 || true' EXIT
run orig 'CUSTOM1=4'
run ours 'CUSTOM1=4 CUSTOM5=1'
trap - EXIT
status=0
for f in "$out"/orig/*.png "$out"/ours/*.png; do
  area=
  case $f in */ours/*) area=$out/ours/area.bin ;; esac
  python3 tools/display.py check "$f" "${f%.png}.frame" $area || status=1
done
for f in "$out"/ours/*.png; do
  [ -f "$out/orig/${f##*/}" ] || continue
  python3 tools/display.py compare "$out/orig/${f##*/}" "$f" "$out/ours/area.bin" || status=1
done
exit $status
