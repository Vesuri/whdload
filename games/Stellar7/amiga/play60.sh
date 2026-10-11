#!/usr/bin/env bash
# Build and play the experimental 60 Hz conversion with normal input and sound.
# CPU/memory/display overrides are the same as run.sh; WHD_ARGS defaults to CUSTOM1=1.
set -euo pipefail
cd "$(dirname "$0")"
. ./env.sh
make -s -C ../whdload sim60
export SLAVE="$PWD/../whdload/Stellar7-Sim60.Slave"
export WHD_ARGS="${WHD_ARGS:-CUSTOM1=1}"
exec bash ./run.sh
