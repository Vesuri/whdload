#!/bin/bash
# tools/gametime.sh [run options]: game time (docs/internals.md#game-time). Two boots: each
# takes the route into landscape 0000 and makes a boulder (the enemies start with the player's
# first action), then records the game's state every field for FIELDS fields (default 4000):
# the first with no input, the second with the pointer held at the right edge (panning). The
# Sentinel turns every 200 ticks and, once it sees the player, drains its energy until it
# dies; tools/gametime.py reports both, in fields. Run options are common/run.sh's.
set -u
cd "$(dirname "$0")/.."
. ../../common/env.sh
export WARP=1 WINDOW=none DETERMINISTIC=1 JOY0=none ENTRY=1 "$@"
export INSTANCE=${INSTANCE:-gametime}   # never the default instance: that is the user's make run
inst=$INSTANCE
out=tmp/gametime/${SETUP:-a500}-$inst; rm -rf "$out"; mkdir -p "$out"
t() { python3 tools/sentinel.py "$@"; }
for mode in idle pan; do
  t serve > "$out/serve-$mode.log" 2>&1 & spid=$!
  for i in $(seq 1 600); do t peek 0x58c6e 2 >/dev/null 2>&1 && break; kill -0 $spid 2>/dev/null || break; sleep 0.5; done
  t route > /dev/null; t fields 300 > /dev/null
  t click > /dev/null; t fields 10 > /dev/null; t pointer 1984 272 > /dev/null
  t key 35 > /dev/null                                  # B: a boulder, the first action
  r=$(t waitfor 0x1784 08 300)
  case $r in at*) ;; *) echo "gametime: no boulder ($r)"; t quit > /dev/null; exit 1;; esac
  if [ $mode = pan ]; then t pointer 2378 1536 > /dev/null; t mouse 20 0 > /dev/null; fi
  t snap ${FIELDS:-4000} "$PWD/$out/$mode.bin" 1700:100 58c6e:2 77c0:1 > /dev/null
  t quit > /dev/null; sleep 2
done
python3 tools/gametime.py "$out"/idle.bin "$out"/pan.bin | tee "$out/report.txt"
