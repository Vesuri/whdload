#!/bin/bash
# Boot a server stopped at the game's entry (the decrypted and relocated program, after the
# slave's patches) for tools/route.py: warp, deterministic, nothing in port 0. Any running
# server of this instance is quit first; a boot that does not reach the entry in 120 s is
# stopped. Run options (SETUP, SLAVE, BUILD, SOURCE, WHD_ARGS, EXTRA_ARGS, INSTANCE, ...)
# pass through.
#   PROG_BASE   the entry: default $400 (1.3, and 2.0 without fast memory); `auto` finds it
#               first with a calibration boot (300 fields at a time until it is in place) (2.0 with the program in fast memory: the
#               level-3 vector $6C holds the base + $4DAC). The same setup and build give
#               the same address every time.
#   tools/boot.sh                      default SETUP=a500
#   SETUP=a1200-030 PROG_BASE=auto tools/boot.sh
set -e
cd "$(dirname "$0")/.."
python3 tools/buggyboy.py quit >/dev/null 2>&1 || true
log=tmp/serve-${INSTANCE:-default}.log
mkdir -p tmp
export SETUP=${SETUP:-a500} WARP=1 WINDOW=none JOY0=none DETERMINISTIC=1

serve() {   # BOOT_BREAK or none; waits until serving
    if [ -n "$1" ]; then
        BOOT_BREAK=$1 python3 tools/buggyboy.py serve >"$log" 2>&1 &
    else
        python3 tools/buggyboy.py serve >"$log" 2>&1 &
    fi
    pid=$!
    for _ in $(seq 240); do
        grep -q 'serving on' "$log" 2>/dev/null && return 0
        kill -0 $pid 2>/dev/null || break
        sleep 0.5
    done
    tail -20 "$log"
    kill $pid 2>/dev/null || true
    make -s stop INSTANCE="${INSTANCE:-default}" || true
    exit 1
}

base=${PROG_BASE:-0x400}
if [ "$base" = auto ]; then
    serve ""
    base=
    for _ in 1 2 3 4 5 6 7 8 9 10; do   # until the game's handler is in: base $400 or 64 KB-aligned
        python3 tools/buggyboy.py gdb 'monitor fields 300' >/dev/null
        v=$(python3 tools/buggyboy.py gdb 'x/wx 0x6c' | sed -n 's/.*:[[:space:]]*0x\([0-9a-fA-F]*\).*/\1/p')
        [ -n "$v" ] || continue
        b=$((0x$v - 0x4DAC))
        if [ $b -eq 1024 ] || [ $((b & 0xffff)) -eq 0 ]; then base=$(printf '0x%x' $b); break; fi
    done
    python3 tools/buggyboy.py quit >/dev/null 2>&1 || true
    wait $pid 2>/dev/null || true   # the calibration server gone before the next starts
    [ -n "$base" ] || { echo "boot.sh: no level-3 vector of the game" >&2; exit 1; }
    echo "program base $base"
fi
serve "$base"
echo "serving ($log), program base $base"
