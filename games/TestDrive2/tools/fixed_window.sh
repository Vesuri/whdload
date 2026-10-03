#!/usr/bin/env bash
# Benchmark window: trace FIELDS fields from the first driving frame of the first attract demo.
#   tools/fixed_window.sh OUTDIR [SLAVE]
# Deterministic boot of the stock-A500-equivalent machine; once `duel` is in memory, break at its
# span filler (duel:0789c, first entered when the demo starts driving), then trace.  The demo
# begins identically every boot (desert, 2.6 miles, 0:00) but is NOT pixel-identical between
# boots, so compare frame rates over this window, not frames (docs/optimisation-plan.md).
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=$1; mkdir -p "$OUT"; FIELDS=${FIELDS:-100}
export CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536 DETERMINISTIC=1 SLAVE="${2:-}"
BASE=0xc00000 SIZE=$((1536 * 1024))
td2() { python3 tools/td2.py "$@"; }
[ -S amiga/.run/td2.sock ] && { td2 quit > /dev/null 2>&1 || true; sleep 1; }
rm -f amiga/.run/serve.log "$OUT/trace.bin"
WARP=1 python3 tools/td2.py serve > amiga/.run/serve.log 2>&1 &
trap 'td2 quit > /dev/null 2>&1 || true' EXIT
until grep -q serving amiga/.run/serve.log 2>/dev/null; do sleep 1; done

dump() { td2 gdb "dump binary memory /tmp/td2-code.bin $BASE $(printf '%#x' $((BASE + SIZE)))" > /dev/null; mv /tmp/td2-code.bin "$OUT/code.bin"; }
hunk=
for _ in $(seq 1 60); do
  td2 wait 1 > /dev/null; dump
  hunk=$(python3 -c "
import sys; sys.path.insert(0, 'tools'); from td2_report import regions
r = {n: lo for lo, hi, n, o in regions(open('$OUT/code.bin', 'rb').read(), $BASE)}
print(hex(r['duel']) if 'duel' in r else '')")
  [ -n "$hunk" ] && break
done
[ -n "$hunk" ] || { echo "duel never appeared in memory" >&2; exit 1; }
echo "duel code hunk at $hunk"
td2 until "$(printf '%#x' $((hunk + 0x0789c)))" | grep -m1 Breakpoint
reply=$(td2 profile "$FIELDS" "$PWD/$OUT/trace.bin")
[ -f "$OUT/trace.bin" ] || { echo "no trace: $reply" >&2; exit 1; }
dump
td2 quit > /dev/null; trap - EXIT
python3 - "$OUT" <<'EOF'
import sys; sys.path.insert(0, 'tools'); import barto
out = sys.argv[1]; t = barto.load(f'{out}/trace.bin')
open(f'{out}/first.png', 'wb').write(t.fields[0].shot)
open(f'{out}/last.png', 'wb').write(t.fields[-1].shot)
EOF
python3 tools/frames.py "$OUT/trace.bin" "$OUT/code.bin" "$BASE" | tee "$OUT/frames.txt"
