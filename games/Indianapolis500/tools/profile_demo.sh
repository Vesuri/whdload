#!/usr/bin/env bash
# Profile the original Indianapolis 500 while its attract demo is driving.  See docs/profiling.md.
# Quick, unanchored look; for A/B numbers use tools/fixed_window.sh.
#   tools/profile_demo.sh [OUTDIR]        default OUTDIR tmp/prof/run
# Env: FIELDS (trace length, 1..100 PAL fields, default 80), CHIP_KB/FAST_KB/EXTRA_ARGS (machine;
# default the stock-A500-equivalent 512K chip + 1.5M slow, no fast), DEMO_TIMEOUT (seconds, 300).
set -euo pipefail
cd "$(dirname "$0")/.."
# common/run.sh runs each instance in tmp/run/<INSTANCE>/; without SLAVE it runs the
# installed v3.0 slave, as this harness always has.
RUN="tmp/run/${INSTANCE:-default}/.run"
export SLAVE="${SLAVE:-original}"
OUT="${1:-tmp/prof/run}"
FIELDS="${FIELDS:-80}"
export CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" EXTRA_ARGS="${EXTRA_ARGS---slow_memory=1536}"
# The game reads the port-0 mouse counters (JOY0DAT, game:0b424); a host mouse over the
# window would change them, so captures run with nothing in port 0.
export JOY0="${JOY0:-none}"
mkdir -p "$OUT" "$RUN"
rm -f "$OUT"/trace.bin "$OUT"/code.bin "$OUT"/report.txt "$OUT"/first.png "$OUT"/last.png
i500() { python3 tools/i500.py "$@"; }

# The code is loaded into "other" memory: fast RAM at $200000 when there is any, else slow RAM.
SLOW_KB=$(sed -n 's/.*--slow_memory=\([0-9]*\).*/\1/p' <<< "$EXTRA_ARGS")
if [ "$FAST_KB" -gt 0 ]; then BASE=0x200000; SIZE=$((FAST_KB * 1024))
else BASE=0xc00000; SIZE=$((${SLOW_KB:-512} * 1024)); fi

[ -S "$RUN"/i500.sock ] && { i500 quit > /dev/null 2>&1 || true; sleep 1; }
WARP=1 python3 tools/i500.py serve > "$RUN"/serve.log 2>&1 &
SERVER=$!
trap 'i500 quit > /dev/null 2>&1 || kill $SERVER 2>/dev/null || true' EXIT
until grep -q serving "$RUN"/serve.log 2>/dev/null; do
  kill -0 $SERVER 2>/dev/null || { cat "$RUN"/serve.log; exit 1; }
  sleep 1
done
head -3 "$RUN"/serve.log

# Boot, intro and credits run in warp; the demo starts by itself (~25 s of emulated time after
# the game starts, most of it a table-building loop at game:2dd06) and keeps running.  Poll
# one-field screenshots until the demo is up, then trace.
deadline=$((SECONDS + ${DEMO_TIMEOUT:-300}))
until i500 shot "$PWD/tmp/poll.png" > /dev/null && python3 tools/ingame.py tmp/poll.png; do
  (( SECONDS < deadline )) || { echo "demo not reached in ${DEMO_TIMEOUT:-300}s" >&2; exit 1; }
  i500 wait 0.5 > /dev/null
done
echo "demo in game; tracing $FIELDS fields"
i500 stop > /dev/null
reply=$(i500 profile "$FIELDS" "$PWD/$OUT/trace.bin")
[ -f "$OUT/trace.bin" ] || { echo "profile failed: $reply" >&2; exit 1; }
# gdb splits arguments at spaces, so dump through a space-free path.
i500 gdb "dump binary memory tmp/i500-code.bin $BASE $(printf '%#x' $((BASE + SIZE)))" > /dev/null
mv tmp/i500-code.bin "$OUT/code.bin"
i500 quit > /dev/null; trap - EXIT

python3 - "$OUT" <<'EOF'
import sys, os
sys.path.insert(0, 'tools'); import _amigaxdev, subprocess; from amigaxdev import barto
out = sys.argv[1]; t = barto.load(f'{out}/trace.bin')
open(f'{out}/first.png', 'wb').write(t.fields[0].shot)
open(f'{out}/last.png', 'wb').write(t.fields[-1].shot)
for n in ('first', 'last'):
    ok = subprocess.run([sys.executable, 'tools/ingame.py', f'{out}/{n}.png']).returncode == 0
    print(f'{n} field in game: {ok}')
    if not ok: sys.exit('the trace left the attract demo; rerun with fewer FIELDS')
EOF
python3 tools/i500_report.py "$OUT/trace.bin" "$OUT/code.bin" --base "$BASE" > "$OUT/report.txt"
python3 tools/frames.py "$OUT/trace.bin" "$OUT/code.bin" "$BASE" | tee -a "$OUT/report.txt"
sed -n '1,4p' "$OUT/report.txt" | cut -c1-200
echo "report: $OUT/report.txt"
