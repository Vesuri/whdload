#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
. tools/env.sh
export FSUAE="$PWD/tmp/profiler-fsuae/fs-uae"
export FSUAE_NATIVE_PROFILE_SHA256="$(cat tmp/build/040-profiler.sha256)"
export CPU=68040 AMIGA_MODEL=A4000 CHIP_KB=2048 FAST_KB=4096 DEBUG_PORT=2463 WHD_ARGS=CUSTOM2=0
export KICKSTART="$AMIGA_SHARE/Kickstarts/kick40068.A1200"
export EXTRA_ARGS='--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true'
steering="${EDGE_STEERING:-0}"
checks=(); [ "$steering" = 0 ] || checks+=(--steering)
prefix="${CAPTURE_PREFIX:-sim-input-edges200-040}"
for mode in ${DETAIL_MODES:-full fast}; do
  detail=0; [ "$mode" = full ] || detail=3
  cap="tmp/prof/$prefix-$mode"
  VERIFY=1 SIM_A4000=1 SIM_MODE_MENU=1 SIM_LIVE_DRIVE=1 TAPE_OPPONENT=1 SIM_INPUT_EDGE_TEST=1 SIM_INPUT_EDGE_STEERING="$steering" TAPE_DETAIL="$detail" tools/build.sh > "tmp/build/edge-$mode-build.log"
  python3 tools/quick_start.py "$cap" --simulation 50 --opponent 1 --tick 160 --detail "$detail"
  python3 tools/profile_window.py "$cap" --fields 250
  python3 tools/driving.py gdb "dump binary memory $cap/end-memory.bin 0x200000 0x600000"
  python3 tools/driving.py quit
  python3 tools/display_check.py "$cap" > "$cap/display-check.stdout"
  python3 tools/presentation_latency.py "$cap" > "$cap/presentation-latency.stdout"
  python3 tools/input_edge_latency.py "$cap" "${checks[@]}" > "$cap/input-edge-latency.stdout"
  python3 - "$cap" <<'PY'
import json,sys
from pathlib import Path
r=json.loads((Path(sys.argv[1])/'input-edge-latency.json').read_text())
print(sys.argv[1],[(e['index'],e['trace']['request_to_sample_fields'],e['trace']['request_to_completed_fields'],e['trace']['request_to_containing_display_fields']) for e in r['edges']],flush=True)
PY
done
VERIFY=1 SIM_A4000=1 SIM_MODE_MENU=1 tools/build.sh > tmp/build/edge-restored-build.log
