#!/bin/bash
# Boot a server for tools/route.py and tools/bench.py: warp, deterministic, nothing in
# port 0 (the mouse comes from monitor mouse), no window. Any running server of this
# instance is quit first; a boot that is not serving in 120 s is stopped. Run options
# (SETUP, EXTRA_ARGS, SLAVE, BUILD, WHD_ARGS, INSTANCE, ...) pass through.
#   SETUP=a1200-030 EXTRA_ARGS=--uae_mmu_model=0 tools/boot.sh && python3 tools/route.py hole1
set -e
cd "$(dirname "$0")/.."
python3 tools/zanygolf.py quit >/dev/null 2>&1 || true
log=tmp/serve-${INSTANCE:-default}.log
mkdir -p tmp
export SETUP=${SETUP:-a500} WARP=1 WINDOW=none JOY0=none DETERMINISTIC=1
python3 tools/zanygolf.py serve >"$log" 2>&1 &
pid=$!
for _ in $(seq 240); do
    grep -q 'serving on' "$log" 2>/dev/null && { echo "serving ($log)"; exit 0; }
    kill -0 $pid 2>/dev/null || break
    sleep 0.5
done
tail -20 "$log"
kill $pid 2>/dev/null || true
make -s stop INSTANCE="${INSTANCE:-default}" || true
exit 1
