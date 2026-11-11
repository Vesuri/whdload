#!/bin/bash
# Boot a server stopped at the game's entry (the decrypted and relocated program, after the
# slave's patches: $400, or PROG_BASE for a build that loads it elsewhere) for tools/route.py:
# warp, deterministic, nothing in port 0. Any running server of this instance is quit first;
# a boot that does not reach the entry in 120 s is stopped. Run options (SETUP, SLAVE, BUILD,
# SOURCE, WHD_ARGS, EXTRA_ARGS, INSTANCE, ...) pass through.
#   tools/boot.sh                      default SETUP=a500
#   SETUP=a1200-030 tools/boot.sh
set -e
cd "$(dirname "$0")/.."
python3 tools/buggyboy.py quit >/dev/null 2>&1 || true
log=tmp/serve-${INSTANCE:-default}.log
mkdir -p tmp
BOOT_BREAK=${PROG_BASE:-0x400} SETUP=${SETUP:-a500} WARP=1 WINDOW=none JOY0=none DETERMINISTIC=1 \
    python3 tools/buggyboy.py serve >"$log" 2>&1 &
for _ in $(seq 240); do
    grep -q 'serving on' "$log" 2>/dev/null && { echo "serving ($log)"; exit 0; }
    kill -0 $! 2>/dev/null || break
    sleep 0.5
done
tail -20 "$log"
kill $! 2>/dev/null || true
make -s stop INSTANCE="${INSTANCE:-default}" || true
exit 1
