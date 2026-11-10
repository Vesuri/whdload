#!/bin/bash
# Boot a server stopped at the game's entry ($D7E2) for tools/route.py: warp, deterministic,
# nothing in port 0. Any running server of this instance is quit first. Run options
# (SETUP, SLAVE, EXTRA_ARGS, INSTANCE, ...) pass through.
#   tools/boot.sh                      default SETUP=a1200-030
#   SETUP=a500 tools/boot.sh
set -e
cd "$(dirname "$0")/.."
python3 tools/encounter.py quit >/dev/null 2>&1 || true
log=tmp/serve-${INSTANCE:-default}.log
mkdir -p tmp
BOOT_BREAK=0xD7E2 SETUP=${SETUP:-a1200-030} WARP=1 WINDOW=none JOY0=none DETERMINISTIC=1 \
    python3 tools/encounter.py serve >"$log" 2>&1 &
for _ in $(seq 240); do
    grep -q 'serving on' "$log" 2>/dev/null && { echo "serving ($log)"; exit 0; }
    kill -0 $! 2>/dev/null || break
    sleep 0.5
done
tail -20 "$log"
exit 1
