#!/usr/bin/env bash
# Run BUILD with WHD_ARGS on SETUP hands-off (QUICKSTART) and report the tick ($535ba) and
# field ($3b796) at which the game is lost (the tick counter falls back), polling every
# STEP seconds for at most MAX polls: defeat.sh BUILD SETUP "WHD_ARGS" [STEP] [MAX]
set -uo pipefail
cd "$(dirname "$0")/.."
. ../../common/env.sh 2>/dev/null
build="$1" setup="$2" args="$3" step="${4:-3}" max="${5:-80}"
srv() { python3 ../../common/tools/game_server.py "$@" 2>/dev/null; }
rd() { srv gdb x/1wx "$1" | awk '/^0x[0-9a-f]*:/ {print $2}' | { read -r v; echo $((v)); }; }
(make serve BUILD="$build" NOBUILD=1 SETUP="$setup" WARP=1 WINDOW=none WB=0 WHD_ARGS="$args" > tmp/serve.log 2>&1 &)
for _ in $(seq 1 60); do srv wait 1 >/dev/null && break; sleep 1; done
last=0 lastf=0 res="not lost after $max polls"
for _ in $(seq "$max"); do
  srv wait "$step" >/dev/null
  t=$(rd 0x535ba); f=$(rd 0x3b796)
  if [ "$t" -lt "$last" ]; then res="lost between tick $last (field $lastf) and the next poll"; break; fi
  last=$t lastf=$f
done
echo "$setup $args: $res; last tick $last field $lastf"
srv quit >/dev/null
make -s stop >/dev/null 2>&1 || true   # the emulator of this game, pid-scoped
sleep 2
