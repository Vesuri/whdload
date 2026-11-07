#!/usr/bin/env bash
# Build and play the fixed-rate conversion with normal input and sound (make play60): the
# release slave, whose CUSTOM1 installs the simulation for the machine's CPU (15 Hz on
# 68000/68010, 60 Hz on 68020+). Every common/run.sh option applies; WHD_ARGS defaults to
# CUSTOM1=1.
set -euo pipefail
COMMON="${COMMON:-$(cd "$(dirname "$0")/../../../common" && pwd)}"
export VARIANT=Stellar7
export WHD_ARGS="${WHD_ARGS:-CUSTOM1=1}"
exec "$COMMON/run.sh"
