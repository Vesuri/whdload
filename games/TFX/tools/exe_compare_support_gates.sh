#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
export DEBUG_PORT=2611 FSUAE="$PWD/tmp/opt20-project-emulator/fs-uae/fs-uae"
export PROFILE_SLAVE="$PWD/tmp/exe-compare/render.slave" DELTA_LISTING="$PWD/tmp/exe-compare/render.lst"
export STEP13_020_FPU=1 STEP13_CPUS='040 030 060 020'
export STEP13_ROWS='040-newfpu 040-auto-original 030-auto-original 060-auto-original 020-newfpu 020-auto-original'
python3 tools/step13_matrix.py "$PWD/tmp/exe-compare/support-gates" candidate
