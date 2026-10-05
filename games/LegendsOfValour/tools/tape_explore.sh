#!/usr/bin/env bash
# Exploration only (not reproducible timing): boot the VERIFY slave with an input tape on the
# A500-equivalent machine and take a screenshot every STEP seconds of warp, COUNT times.
# Each shot is labelled with the tape field it was taken at (fields.txt), to set the waits.
#   tools/tape_explore.sh SCRIPT.txt OUTDIR [COUNT [STEP]]      KEEP=1 leaves the emulator running
set -euo pipefail
cd "$(dirname "$0")/.."
export FSUAE_RUN="${FSUAE_RUN:-.cap}"; CAP=$FSUAE_RUN; mkdir -p "amiga/$CAP"
SCRIPT=$1 OUT=$2 COUNT=${3:-8} STEP=${4:-5}
mkdir -p "$OUT"; rm -f "$OUT"/shot*.png
make -s -C whdload verify > /dev/null
cp tmp/build/LegendsOfValour.Slave "$OUT/slave.slave"
TAPEFIELD=$(LC_ALL=C sed -n 's/^_tapefield  *00:\([0-9A-F]*\) *$/0x\1/p' tmp/build/LegendsOfValour.lst | head -1)
python3 tools/tape.py "$SCRIPT" "$OUT/tape.bin" > /dev/null
export SLAVE="$PWD/$OUT/slave.slave" TAPE="$PWD/$OUT/tape.bin" WHD_ARGS="CUSTOM5=1 ${WHD_ARGS:-}" \
  JOY0=none CHIP_KB=${CHIP_KB:-512} FAST_KB=${FAST_KB:-0} EXTRA_ARGS=${EXTRA_ARGS---slow_memory=1536} WARP=1
SLOW_KB=$(sed -n 's/.*--slow_memory=\([0-9]*\).*/\1/p' <<< "$EXTRA_ARGS")
if [ "$FAST_KB" -gt 0 ]; then BASE=0x200000; SIZE=$((FAST_KB * 1024))
else BASE=0xc00000; SIZE=$((${SLOW_KB:-512} * 1024)); fi
[ -S amiga/$CAP/lov.sock ] && { python3 tools/lov.py quit > /dev/null 2>&1 || true; sleep 1; }
rm -f amiga/$CAP/serve.log
python3 tools/lov.py serve > amiga/$CAP/serve.log 2>&1 &
[ "${KEEP:-0}" = 1 ] || trap 'python3 tools/lov.py quit > /dev/null 2>&1 || true' EXIT
until grep -q serving amiga/$CAP/serve.log 2>/dev/null; do sleep 1; done
# The live slave's address, for reading _tapefield.
slave=
for _ in $(seq 1 60); do
  python3 tools/lov.py wait 0.5 > /dev/null
  python3 tools/lov.py gdb "dump binary memory /tmp/lov-explore-$$.bin $BASE $(printf %#x $((BASE + SIZE)))" > /dev/null
  slave=$(SLAVE="$OUT/slave.slave" python3 -c "
import sys; sys.path.insert(0, 'tools'); from lov_report import regions
r = {n: lo for lo, hi, n, o in regions(open('/tmp/lov-explore-$$.bin', 'rb').read(), $BASE)}
print(r.get('slave', ''))")
  [ -n "$slave" ] && break
done
echo "slave $slave" > "$OUT/slave.txt"; rm -f /tmp/lov-explore-$$.bin "$OUT/fields.txt"
for i in $(seq -w 1 "$COUNT"); do
  python3 tools/lov.py wait "$STEP" > /dev/null
  python3 tools/lov.py shot "$PWD/$OUT/shot$i.png" > /dev/null
  f=$(python3 tools/lov.py gdb "x/1uw $((slave + TAPEFIELD))" | awk 'END {print $NF}')
  echo "shot$i $f" | tee -a "$OUT/fields.txt"
done
python3 - "$OUT" <<'PY'
import sys, glob
from PIL import Image
from PIL import ImageDraw
fs = sorted(glob.glob(f'{sys.argv[1]}/shot*.png')); ims = [Image.open(f).convert('RGB') for f in fs]
lab = dict(l.split() for l in open(f'{sys.argv[1]}/fields.txt'))
for f, im in zip(fs, ims):
    ImageDraw.Draw(im).text((8, 8), 'field ' + lab.get(f.rsplit('/', 1)[1][:-4], '?'), fill=(255, 255, 0))
w, h = ims[0].size; cols = 4; rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * w // 2, rows * h // 2))
for i, im in enumerate(ims): sheet.paste(im.resize((w // 2, h // 2)), ((i % cols) * w // 2, (i // cols) * h // 2))
sheet.save(f'{sys.argv[1]}/sheet.png'); print(f'{sys.argv[1]}/sheet.png')
PY
