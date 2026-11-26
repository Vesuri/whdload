#!/bin/bash
# Still frames for comparing two builds' pens (resolution plan step 7): the frame each shows
# at the same places, from its chunky buffer (ab3d.py chunky), the c2p's input.
#
#   tools/pencheck.sh OUT [LEVELS]     then  python3 tools/pendiff.py REF OUT
#
#   OUT      directory for the frames (under tmp/)
#   LEVELS   how many levels from level 1 (default 3; F1 skips to the next, CUSTOM1=4)
#
# The build is the run's (SLAVE=path or BUILD=name, common/run.sh), always with CUSTOM5=1;
# made beforehand (make build BUILD=name): the run does not rebuild it (NOBUILD=1).
# One boot, deterministic (WARP=1 DETERMINISTIC=1 JOY0=none), on SETUP (default a1200-030;
# not a 68040, whose copyback cache can hold the buffer's last writes). In each level, at
# its start and 40 fields forward, the view turns 8 times by about 45 degrees with the
# mouse, which places the player exactly on any CPU (mouse moves add up; keys go by time).
# At each place it stands 50 fields, then the frame goes to OUT/L-P-A-V.pens (level, place,
# angle, view s or f); each place is seen in the small view, then in full screen.
set -eu
out=$1 levels=${2:-3}
game=$(cd "$(dirname "$0")/.." && pwd)
cd "$game"
. ../../common/env.sh
mkdir -p "$out"
out=$(cd "$out" && pwd)
export NOBUILD=1 INSTANCE=pencheck WARP=1 WINDOW=none DETERMINISTIC=1 JOY0=none
export SETUP=${SETUP:-a1200-030} WHD_ARGS="CUSTOM5=1 CUSTOM1=4"

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
level=1
while :; do
  for place in 0 1; do
    [ $place = 0 ] || ab3d play '40 my -10; 10' > /dev/null
    for view in s f; do
      [ $view = s ] && ab3d full 0 > /dev/null || ab3d full 1 > /dev/null
      for angle in 0 1 2 3 4 5 6 7; do
        ab3d play '11 mx 23; 50' > /dev/null
        ab3d chunky "$out/$level-$place-$angle-$view.pens" > /dev/null
      done
    done
  done
  ab3d full 0 > /dev/null
  echo "level $level: $(ls "$out"/$level-*.pens | wc -l | tr -d ' ') frames" | tee -a "$out/log.txt"
  [ $level -lt "$levels" ] || break
  level=$((level + 1))
  ab3d next | tee -a "$out/log.txt"
done
