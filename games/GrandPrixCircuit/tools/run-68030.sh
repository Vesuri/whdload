#!/usr/bin/env bash
# Boot on the harness's A1200 with a cycle-exact 25 MHz 68030 (make run-68030).
# Takes the run options of common/run.sh; SLAVE=original boots the shipped slave.
set -euo pipefail
cd "$(dirname "$0")/.."
. ../../common/env.sh
export AMIGA_MODEL=A1200 CPU=68030 CHIP_KB=2048 FAST_KB=4096 SLOW_KB=0
export KICKSTART="$KICKSTART_A1200"
export EXTRA_ARGS="${EXTRA_ARGS:-} --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true"
exec ../../common/run.sh run
