#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
. tools/env.sh
export FSUAE="$PWD/tmp/contact-write-fsuae/fs-uae"
export FSUAE_NATIVE_PROFILE_SHA256=9ba1014bf53e03853ada0b02e13073736d9dba90ce355a980a6af4f7084f0e5f
export CPU=68040 AMIGA_MODEL=A4000 CHIP_KB=2048 FAST_KB=4096 DEBUG_PORT=2501 WHD_ARGS=CUSTOM2=1
export KICKSTART="$AMIGA_SHARE/Kickstarts/kick40068.A1200"
export EXTRA_ARGS='--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_blitter_cycle_exact=true --uae_immediate_blits=false'
cap=tmp/prof/current-steering-fast
mkdir -p tmp/build/current-steering-backup
cp tmp/build/4DSportsDriving-verify.slave tmp/build/4DSportsDriving-verify.lst tmp/build/current-steering-backup/
VERIFY=1 SIM_A4000=1 SIM_STARTUP_TESTS=0 SIM_MODE_MENU=1 SIM_LIVE_DRIVE=1 TAPE_OPPONENT=1 SIM_INPUT_EDGE_TEST=1 SIM_INPUT_EDGE_STEERING=1 TAPE_DETAIL=3 tools/build.sh > tmp/build/current-steering-fast.log 2>&1
python3 tools/quick_start.py "$cap" --simulation 50 --opponent 1 --tick 160 --detail 3
python3 tools/profile_window.py "$cap" --fields 250
python3 tools/driving.py gdb "dump binary memory $cap/end-memory.bin 0x200000 0x600000"
python3 tools/driving.py quit
python3 tools/display_check.py "$cap" > "$cap/display-check.stdout"
python3 tools/presentation_latency.py "$cap" > "$cap/presentation-latency.stdout"
python3 tools/input_edge_latency.py "$cap" --steering > "$cap/input-edge-latency.stdout"
