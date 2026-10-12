#!/usr/bin/env bash
# Build and play the experimental fixed-rate conversion with normal input and sound.
# Select the fixed rate by CPU; CPU/memory/display overrides match run.sh.
# WHD_ARGS defaults to CUSTOM1=1. Both builds use the same real-time game units.
set -euo pipefail
cd "$(dirname "$0")"
. ./env.sh
case "${CPU:-68000}" in
  68000|68010)
    target=sim68000
    slave_name=Stellar7-Sim68000.Slave
    ;;
  68020|68EC020|68030|68EC030|68040*|68EC040*|68060*|68EC060*)
    target=sim60
    slave_name=Stellar7-Sim60.Slave
    ;;
  *)
    echo "Unsupported CPU for fixed-rate selection: $CPU" >&2
    exit 1
    ;;
esac
make -s -C ../whdload "$target"
export SLAVE="$PWD/../whdload/$slave_name"
export WHD_ARGS="${WHD_ARGS:-CUSTOM1=1}"
exec bash ./run.sh
