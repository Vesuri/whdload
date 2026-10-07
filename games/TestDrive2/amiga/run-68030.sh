#!/usr/bin/env bash
# Play the PAL A1200 + 68030/25 MHz configuration.
# SLAVE=path selects an existing normal release build; otherwise build one.
#   amiga/run-68030.sh
set -euo pipefail
cd "$(dirname "$0")/.."
source amiga/env.sh
if [ "$#" -ne 0 ]; then
  echo 'Usage: amiga/run-68030.sh' >&2
  exit 2
fi
if [ -z "${SLAVE:-}" ]; then
  make -s -C whdload > /dev/null
  export SLAVE="$PWD/whdload/TestDrive2.slave"
else
  export SLAVE="$(cd "$(dirname "$SLAVE")" && pwd)/$(basename "$SLAVE")"
fi
export AMIGA_MODEL=A1200 CPU=68030 CHIP_KB=2048 FAST_KB=4096
export KICKSTART="$KICKSTART_DIR/kick40068.A1200"
export EXTRA_ARGS='--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true'
export WHD_ARGS="${WHD_ARGS:-CUSTOM2=1}"
# Interactive play uses real wall time, sound and no debugging instrument.
export WARP=0 SILENT=0 DEBUG=0 DETERMINISTIC=0
unset BOOT_BREAK RECORD
exec amiga/run.sh
