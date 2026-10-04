#!/usr/bin/env bash
# Build the patched slave and play it on an expanded A1200 (68EC020, 2 MB chip, 4 MB fast).
#   amiga/run-a1200.sh                     patched: CUSTOM2=3 (simulation + blitter priority)
#   WHD_ARGS=CUSTOM2=0 amiga/run-a1200.sh  the original game, same machine
#   CPU=68030 amiga/run-a1200.sh           a 25 MHz 68030 instead
set -euo pipefail
cd "$(dirname "$0")/.."
. amiga/env.sh
make -s -C whdload > /dev/null
export SLAVE="$PWD/whdload/TestDrive2.slave"
export AMIGA_MODEL=A1200 CPU="${CPU:-68EC020}" CHIP_KB=2048 FAST_KB=4096
export KICKSTART="/path/to/kickstarts/kick40068.A1200"
export WHD_ARGS="${WHD_ARGS:-CUSTOM2=3}"
if [ "$CPU" = 68030 ]; then
  export EXTRA_ARGS="--uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true"
fi
exec amiga/run.sh
