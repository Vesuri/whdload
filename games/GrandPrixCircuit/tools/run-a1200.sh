#!/usr/bin/env bash
# Boot on the harness's A1200: 68EC020, 2 MB chip + 4 MB fast, Kickstart 3.1 (make run-a1200).
# Takes the run options of common/run.sh; SLAVE=original boots the shipped slave.
set -euo pipefail
cd "$(dirname "$0")/.."
. ../../common/env.sh
export AMIGA_MODEL=A1200 CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 SLOW_KB=0
export KICKSTART="$KICKSTART_A1200"
exec ../../common/run.sh run
