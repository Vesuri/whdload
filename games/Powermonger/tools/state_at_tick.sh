#!/usr/bin/env bash
# Boot BUILD with WHD_ARGS on SETUP, stop at the world step of tick TICK ($535ba) and dump
# chip memory 0-$80000 to OUT: state_at_tick.sh BUILD SETUP "WHD_ARGS" TICK OUT
# Calls game_server.py directly: make server passes CMD through the shell.
set -uo pipefail
cd "$(dirname "$0")/.."
. ../../common/env.sh 2>/dev/null
build="$1" setup="$2" args="$3" tick="$4" out="$(cd "$(dirname "$5")" && pwd)/$(basename "$5")"
srv() { python3 ../../common/tools/game_server.py "$@" 2>/dev/null; }
(make serve BUILD="$build" NOBUILD=1 SETUP="$setup" WARP=1 WINDOW=none WB=0 WHD_ARGS="$args" > tmp/serve.log 2>&1 &)
for _ in $(seq 1 60); do srv wait 1 >/dev/null && break; sleep 1; done
srv stop >/dev/null
srv gdb "break *0x12952 if *(int*)0x535ba == $tick" >/dev/null
srv gdb continue | grep -i breakpoint | head -1
srv gdb delete >/dev/null
srv gdb x/1wx 0x535ba | grep '^0x5'
srv gdb dump binary memory "$out" 0 0x80000 >/dev/null
srv quit >/dev/null
make -s stop >/dev/null 2>&1 || true   # the emulator of this game, pid-scoped
sleep 2
