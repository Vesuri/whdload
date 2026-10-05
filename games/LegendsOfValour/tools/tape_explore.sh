#!/usr/bin/env bash
# Exploration only (not reproducible timing): boot the VERIFY slave with an input tape on the
# A500-equivalent machine and take a screenshot every STEP seconds of warp, COUNT times.
#   tools/tape_explore.sh SCRIPT.txt OUTDIR [COUNT [STEP]]      KEEP=1 leaves the emulator running
set -euo pipefail
cd "$(dirname "$0")/.."
SCRIPT=$1 OUT=$2 COUNT=${3:-8} STEP=${4:-5}
mkdir -p "$OUT"; rm -f "$OUT"/shot*.png
make -s -C whdload verify > /dev/null
cp whdload/LegendsOfValour.Slave "$OUT/slave.slave"
python3 tools/tape.py "$SCRIPT" "$OUT/tape.bin" > /dev/null
export SLAVE="$PWD/$OUT/slave.slave" TAPE="$PWD/$OUT/tape.bin" WHD_ARGS="CUSTOM5=1 ${WHD_ARGS:-}" \
  JOY0=none CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536 WARP=1
[ -S amiga/.run/lov.sock ] && { python3 tools/lov.py quit > /dev/null 2>&1 || true; sleep 1; }
rm -f amiga/.run/serve.log
python3 tools/lov.py serve > amiga/.run/serve.log 2>&1 &
[ "${KEEP:-0}" = 1 ] || trap 'python3 tools/lov.py quit > /dev/null 2>&1 || true' EXIT
until grep -q serving amiga/.run/serve.log 2>/dev/null; do sleep 1; done
for i in $(seq -w 1 "$COUNT"); do
  python3 tools/lov.py wait "$STEP" > /dev/null
  python3 tools/lov.py shot "$PWD/$OUT/shot$i.png" > /dev/null
done
python3 - "$OUT" <<'PY'
import sys, glob
from PIL import Image
fs = sorted(glob.glob(f'{sys.argv[1]}/shot*.png')); ims = [Image.open(f).convert('RGB') for f in fs]
w, h = ims[0].size; cols = 4; rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * w // 2, rows * h // 2))
for i, im in enumerate(ims): sheet.paste(im.resize((w // 2, h // 2)), ((i % cols) * w // 2, (i // cols) * h // 2))
sheet.save(f'{sys.argv[1]}/sheet.png'); print(f'{sys.argv[1]}/sheet.png')
PY
