#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
. tools/env.sh
export GAME_SOURCE="$PWD/tmp/fixtures/display-wait-uninstrumented/source"
export FSUAE="$PWD/tmp/profiler-fsuae/fs-uae"
export FSUAE_NATIVE_PROFILE_SHA256="$(cat tmp/build/040-profiler.sha256)"
export CPU=68040 AMIGA_MODEL=A4000 CHIP_KB=2048 FAST_KB=4096 DEBUG_PORT=2481 WHD_ARGS=CUSTOM2=0
export KICKSTART="$AMIGA_SHARE/Kickstarts/kick40068.A1200"
export EXTRA_ARGS='--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_blitter_cycle_exact=true --uae_immediate_blits=false'
for mode in fast full; do
 detail=3; [ "$mode" = fast ] || detail=0
 cap="tmp/prof/display-wait-uninstrumented-$mode"
 VERIFY=1 SIM_A4000=1 SIM_STARTUP_TESTS=0 SIM_MODE_MENU=1 SIM_LIVE_DRIVE=1 TAPE_OPPONENT=1 SIM_INPUT_EDGE_TEST=1 SIM_INPUT_EDGE_STEERING=1 TAPE_DETAIL="$detail" tools/build.sh > "tmp/build/display-wait-uninstrumented-$mode.log" 2>&1
 python3 tools/quick_start.py "$cap" --simulation 50 --opponent 1 --tick 160 --detail "$detail"
 cp tmp/run/default/.run/fsuae/Cache/Logs/debug.uae "$cap/effective-debug.uae"
 python3 tools/profile_window.py "$cap" --fields 250
 python3 tools/driving.py gdb "dump binary memory $cap/end-memory.bin 0x200000 0x600000"
 python3 tools/driving.py quit
 python3 tools/display_check.py "$cap" > "$cap/display-check.stdout"
 python3 tools/render_blitter_overlap.py "$cap" --display-maps > "$cap/render-blitter-overlap.stdout"
 python3 tools/presentation_latency.py "$cap" > "$cap/presentation-latency.stdout"
 python3 tools/input_edge_latency.py "$cap" --steering > "$cap/input-edge-latency.stdout"
done
unset GAME_SOURCE
VERIFY=1 SIM_A4000=1 tools/build.sh > tmp/build/display-wait-uninstrumented-restore.log 2>&1
