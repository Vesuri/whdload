#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
. tools/env.sh
export CPU=68020 AMIGA_MODEL=A1200 CHIP_KB=2048 FAST_KB=4096 DEBUG_PORT=2483 WHD_ARGS=CUSTOM2=0
export KICKSTART="$AMIGA_SHARE/Kickstarts/kick40063.A600"
export GAME_SOURCE="$PWD/tmp/fixtures/display-wait-uninstrumented/source"
cap=tmp/prof/display-wait-seek50
VERIFY=1 SIM_A4000=1 SIM_HISTORY_TEST_SPACING=50 SIM_HISTORY_SEEK_TEST=1 SIM_HISTORY_SEEK_TARGET=155 tools/build.sh > tmp/build/display-wait-seek50.log 2>&1
python3 tools/quick_start.py "$cap" --simulation 50 --tick 155
python3 tools/replay_snapshot_check.py "$cap" --slot 3 --replay-tick 155
python3 tools/driving.py quit
unset GAME_SOURCE
VERIFY=1 SIM_A4000=1 tools/build.sh > tmp/build/display-wait-seek-restore.log 2>&1
