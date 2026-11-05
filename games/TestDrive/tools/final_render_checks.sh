#!/bin/bash
set -euo pipefail
. "$(dirname "$0")/env.sh"
cd "$HARNESS_ROOT"
python3 tools/render_capture.py final-zero-off --c1 32112656 --c5 105 > tmp/phase10/final-zero-off.log 2>&1
python3 tools/render_capture.py final-zero-on --c1 32112640 --c5 105 > tmp/phase10/final-zero-on.log 2>&1
python3 tools/zero_render.py tmp/phase10/final-zero-off/view-0 tmp/phase10/final-zero-on/view-0 > tmp/phase10/final-zero.json
python3 tools/check_render_units.py tmp/phase10/final-zero-on/end/code.bin > tmp/phase10/final-units.json
python3 tools/render_capture.py final-downhill --c1 55050240 --c5 3221225569 > tmp/phase10/final-downhill.log 2>&1
python3 tools/subunit_geometry.py tmp/phase10/final-downhill/view-0 > tmp/phase10/final-downhill.json
python3 tools/render_profile.py final-cost-demo --c5 0 --settle 1000 > tmp/phase10/final-cost-demo.log 2>&1
python3 tools/subunit_cost.py tmp/phase10/final-cost-demo > tmp/phase10/final-cost-demo.json
for preset in a1200 a500 a1200-030; do
 for arm in off on; do
  c1=0
  if [ "$arm" = off ]; then c1=16; fi
  python3 tools/render_benchmark.py "matrix4-$preset-$arm" --preset "$preset" --c1 "$c1" > "tmp/phase10/matrix4-$preset-$arm.log" 2>&1
 done
 python3 - "$preset" <<'CHECK'
import json,sys
from pathlib import Path
p=Path('tmp/phase10');n=sys.argv[1]
for w in range(2):
 r=[json.loads((p/('matrix4-'+n+'-'+a)/('window-'+str(w))/'swaps.json').read_text())['window_fps'] for a in ['off','on']]
 print(n,w,r,flush=True);assert r[1]>=r[0],(n,w,r)
CHECK
done
python3 tools/check_render.py --prefix matrix4-
python3 tools/render_normal_capture.py final-normal-off --preset a1200 --c2 0 --fields 400 > tmp/phase10/final-normal-off.log 2>&1
python3 tools/render_normal_capture.py final-normal-on --preset a1200 --c2 1 --fields 400 > tmp/phase10/final-normal-on.log 2>&1
for arm in off on; do
 python3 tools/check_disabled.py "tmp/phase10/final-normal-$arm" > "tmp/phase10/final-normal-$arm-bytes.json"
done
