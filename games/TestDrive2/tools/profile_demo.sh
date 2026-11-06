#!/usr/bin/env bash
# Profile the original Test Drive II while its attract demo is driving.  See docs/testing.md.
#   tools/profile_demo.sh [OUTDIR]        default OUTDIR tmp/prof/run
# Env: FIELDS (trace length, 1..100 PAL fields, default 80), CHIP_KB/FAST_KB/EXTRA_ARGS (machine;
# default the stock-A500-equivalent 512K chip + 1.5M slow, no fast), DEMO_TIMEOUT (seconds, 300).
set -euo pipefail
cd "$(dirname "$0")/.."
RUN="tmp/run/${INSTANCE:-default}/.run"
OUT="${1:-tmp/prof/run}"
FIELDS="${FIELDS:-80}"
export CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" EXTRA_ARGS="${EXTRA_ARGS---slow_memory=1536}"
mkdir -p "$OUT" "$RUN"
rm -f "$OUT"/trace.bin "$OUT"/code.bin "$OUT"/report.txt "$OUT"/first.png "$OUT"/last.png
td2() { python3 tools/td2.py "$@"; }

# The code is loaded into "other" memory: fast RAM at $200000 when there is any, else slow RAM.
SLOW_KB=$(sed -n 's/.*--slow_memory=\([0-9]*\).*/\1/p' <<< "$EXTRA_ARGS")
export SLOW_KB
if [ "$FAST_KB" -gt 0 ]; then BASE=0x200000; SIZE=$((FAST_KB * 1024))
else BASE=0xc00000; SIZE=$((${SLOW_KB:-512} * 1024)); fi

[ -S "$RUN/td2.sock" ] && { td2 quit > /dev/null 2>&1 || true; sleep 1; }
SLAVE="${SLAVE:-original}" WARP=1 python3 tools/td2.py serve > $RUN/serve.log 2>&1 &
SERVER=$!
trap 'td2 quit > /dev/null 2>&1 || kill $SERVER 2>/dev/null || true' EXIT
until grep -q serving $RUN/serve.log 2>/dev/null; do
  kill -0 $SERVER 2>/dev/null || { cat $RUN/serve.log; exit 1; }
  sleep 1
done
head -3 $RUN/serve.log

# Boot, intro and menus run in warp; the demo starts by itself.  Poll one-field screenshots
# until the driving view is up, then trace immediately (the demo only lasts a few seconds).
deadline=$((SECONDS + ${DEMO_TIMEOUT:-300}))
until td2 shot "$PWD/$RUN/poll.png" > /dev/null && python3 tools/ingame.py $RUN/poll.png; do
  (( SECONDS < deadline )) || { echo "demo not reached in ${DEMO_TIMEOUT:-300}s" >&2; exit 1; }
  td2 wait 0.5 > /dev/null
done
echo "demo in game; tracing $FIELDS fields"
td2 stop > /dev/null
reply=$(td2 profile "$FIELDS" "$PWD/$OUT/trace.bin")
[ -f "$OUT/trace.bin" ] || { echo "profile failed: $reply" >&2; exit 1; }
# gdb splits arguments at spaces: the path must have none.
td2 gdb "dump binary memory $PWD/$OUT/code.bin $BASE $(printf '%#x' $((BASE + SIZE)))" > /dev/null
td2 quit > /dev/null; trap - EXIT

python3 - "$OUT" <<'EOF'
import sys, os
sys.path.insert(0, 'tools'); import subprocess, _amigaxdev; from amigaxdev import barto
out = sys.argv[1]; t = barto.load(f'{out}/trace.bin')
open(f'{out}/first.png', 'wb').write(t.fields[0].shot)
open(f'{out}/last.png', 'wb').write(t.fields[-1].shot)
for n in ('first', 'last'):
    ok = subprocess.run([sys.executable, 'tools/ingame.py', f'{out}/{n}.png']).returncode == 0
    print(f'{n} field in game: {ok}')
    if not ok: sys.exit('the trace left the in-game demo; rerun with fewer FIELDS')
EOF
python3 tools/td2_report.py "$OUT/trace.bin" "$OUT/code.bin" --base "$BASE" > "$OUT/report.txt"
python3 tools/frames.py "$OUT/trace.bin" "$OUT/code.bin" "$BASE" | tee -a "$OUT/report.txt"
sed -n '1,4p' "$OUT/report.txt" | cut -c1-200
echo "report: $OUT/report.txt"
