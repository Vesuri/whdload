#!/bin/bash
# The two-player link (resolution plan step 8).
#
#   tools/link.sh [OUT [SETUP [WHD_ARGS]]]   OUT default tmp/link, WHD_ARGS default CUSTOM5=1
#
# Two emulators (INSTANCE=link1, link2) whose serial ports are joined through two
# pseudo-terminals (tools/ptylink.py). The second selects 2 PLAYER SLAVE and PLAY GAME,
# the first 2 PLAYER MASTER and PLAY GAME; then both play 600 fields at once in the small
# view and 600 in full screen, the master walking and turning with the mouse, the slave on
# the arrow keys, counting each one's frames. Screenshots in OUT. Exit status 1 when either
# draws no frame in a part or no bytes cross the link.
set -eu
game=$(cd "$(dirname "$0")/.." && pwd)
cd "$game"
. ../../common/env.sh
out=${1:-tmp/link}
[ -n "${2:-}" ] && export SETUP=$2
args=${3:-CUSTOM5=1}
mkdir -p "$out"
out=$(cd "$out" && pwd)
export WARP=1 WINDOW=none JOY0=none
# one build for both (NOBUILD=1: the existing one)
[ "${NOBUILD:-0}" = 1 ] || ../../common/build.sh release > /dev/null
export NOBUILD=1

a() { local i=$1; shift; INSTANCE=link$i python3 tools/ab3d.py "$@"; }
k() { a "$1" key "$2" > /dev/null; }
both() {    # both CMD...: the same command on both at once
  a 1 "$@" > "$out/.both1" & p1=$!
  a 2 "$@" > "$out/.both2" & p2=$!
  wait $p1; wait $p2
}
relay=
stop() {
  a 1 quit > /dev/null 2>&1 || true
  a 2 quit > /dev/null 2>&1 || true
  [ -z "$relay" ] || kill "$relay" 2> /dev/null || true
}
trap stop EXIT

python3 -I tools/ptylink.py "$out/relay.txt" > "$out/ttys" &
relay=$!
i=0
until [ -s "$out/ttys" ]; do i=$((i + 1)); [ $i -lt 20 ] || exit 1; sleep 0.25; done
set -- $(cat "$out/ttys")
ttys1=$1 ttys2=$2
for i in 1 2; do
  eval tty=\$ttys$i
  rm -f tmp/run/link$i/.run/ab3d.sock
  INSTANCE=link$i WHD_ARGS=$args EXTRA_ARGS="${EXTRA_ARGS:-} --serial_port=$tty" \
    python3 tools/ab3d.py serve > "$out/serve$i.log" 2>&1 &
done
i=0
until grep -q '^serving' "$out/serve1.log" && grep -q '^serving' "$out/serve2.log"; do
  i=$((i + 1))
  [ $i -lt 240 ] || { echo 'servers did not start' >&2; exit 1; }
  sleep 0.5
done
both wait 20
# the menu: up to 1 PLAYER; RETURN makes it 2 PLAYER MASTER; on that line RETURN again
# makes it 2 PLAYER SLAVE; PLAY GAME is below. The slave waits for the master.
k 2 4c; k 2 44; k 2 4c; k 2 44; k 2 44
k 1 4c; k 1 44; k 1 4d; k 1 44
both play 300
k 1 37   # M: the master on the mouse
status=0
part() {    # part NAME: both play 600 fields, counting frames
  a 1 frames 600 '200 my -8; 200 mx 15; 200 my -8 fire' > "$out/$1-1.txt" & p1=$!
  a 2 frames 600 '300 key 4f; 300 key 4c' > "$out/$1-2.txt" & p2=$!
  wait $p1; wait $p2
  for i in 1 2; do
    echo "$1, player $i: $(cat "$out/$1-$i.txt")"
    grep -q ' 0 whole frames' "$out/$1-$i.txt" && status=1
    a $i shot "$out/$1-$i.png" > /dev/null
  done
}
part small
both full 1
part full
sleep 1.5
echo "link bytes: $(cat "$out/relay.txt")"
grep -q '^1->2 0 \|2->1 0$' "$out/relay.txt" && status=1
rm -f "$out/.both1" "$out/.both2"
exit $status
