#!/bin/bash
set -euo pipefail
. "$(dirname "$0")/env.sh"
cd "$HARNESS_ROOT"
P=tmp/phase11
python3 tools/report_simulation_handling.py "$P/release-matrix.json" > "$P/handling.json"
for preset in a500 a1200; do
 python3 tools/release_simulation_capture.py "events-$preset" --preset "$preset" --c1 2 --c5 23 --fields 2100 > "$P/events-$preset.log" 2>&1
 python3 tools/check_police.py "$P/events-$preset" > "$P/events-$preset.json"
 python3 tools/release_simulation_capture.py "demo-$preset" --preset "$preset" --c1 4 --c5 0 --fields 1600 > "$P/demo-$preset.log" 2>&1
done
python3 tools/release_simulation_capture.py route-a500 --preset a500 --c1 4 --c5 1 > "$P/route-a500.log" 2>&1
python3 tools/release_simulation_capture.py slow-a1200 --preset a1200 --c5 1 --c4 1 > "$P/slow-a1200.log" 2>&1
python3 tools/release_simulation_capture.py verify-disabled --preset a1200 --c2 0 --c3 0 --c5 0 --fields 100 > "$P/verify-disabled.log" 2>&1
python3 tools/check_disabled.py "$P/verify-disabled" > "$P/verify-disabled.json"
python3 tools/release_render_capture.py zero-off --c1 32112656 --c5 105 > "$P/zero-off.log" 2>&1
python3 tools/release_render_capture.py zero-on --c1 32112640 --c5 105 > "$P/zero-on.log" 2>&1
python3 tools/zero_render.py "$P/zero-off/view-0" "$P/zero-on/view-0" > "$P/zero.json"
python3 tools/check_render_units.py "$P/zero-on/end/code.bin" > "$P/render-units.json"
python3 tools/release_render_capture.py downhill --c1 55050240 --c5 3221225569 > "$P/downhill.log" 2>&1
python3 tools/subunit_geometry.py "$P/downhill/view-0" > "$P/downhill.json"
for settle in 0 1000 1600; do
 python3 tools/release_normal_render_profile.py "normal-cost-$settle" --settle "$settle" > "$P/normal-cost-$settle.log" 2>&1
 python3 tools/subunit_cost.py "$P/normal-cost-$settle" > "$P/normal-cost-$settle.json"
done
for preset in a500 a1200 a1200-030; do
 for arm in off on; do
  c1=0; c2=1
  if [ "$arm" = off ]; then c1=16; c2=0; fi
  python3 tools/release_render_benchmark.py "projection-$preset-$arm" --preset "$preset" --c1 "$c1" > "$P/projection-$preset-$arm.log" 2>&1
  python3 tools/release_normal_render_benchmark.py "normal-$preset-$arm" --preset "$preset" --c2 "$c2" > "$P/normal-$preset-$arm.log" 2>&1
 done
done
python3 tools/release_check_render.py --prefix projection- > "$P/projection-fps.json"
for version in 19.2 20.0; do
 case "$version" in
  19.2) export WHDLOAD_BINARY="$AMIGA_SHARE/WHDLoad/C/WHDLoad" ;;
  20.0) export WHDLOAD_BINARY="$AMIGA_SHARE/WHDLoad-20.0/C/WHDLoad" ;;
 esac
 for arm in off on; do
  c2=1; if [ "$arm" = off ]; then c2=0; fi
  python3 tools/release_render_normal_capture.py "whd-$version-$arm" --preset a1200 --c2 "$c2" --fields 400 > "$P/whd-$version-$arm.log" 2>&1
  python3 tools/check_disabled.py "$P/whd-$version-$arm" > "$P/whd-$version-$arm.json"
 done
done
