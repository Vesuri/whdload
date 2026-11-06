#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
export DEBUG_PORT=2611 FSUAE="$PWD/tmp/opt20-project-emulator/fs-uae/fs-uae"
export PROFILE_SLAVE="$PWD/tmp/exe-compare/auto.slave" DELTA_LISTING="$PWD/tmp/exe-compare/auto.lst"
export STEP13_020_FPU=68882 STEP13_CPUS='040 030 060 020' AUTO_FPU_CPUS='020 030 040 060'
python3 tools/step13_matrix.py "$PWD/tmp/exe-compare/selection" candidate
unset STEP13_020_FPU
export STEP13_CPUS=020 AUTO_FPU_CPUS='030 040 060'
python3 tools/step13_matrix.py "$PWD/tmp/exe-compare/selection-no-fpu" candidate
export STEP13_020_FPU=68881 AUTO_FPU_CPUS='020 030 040 060' STEP13_ROWS='020-auto 020-auto-original'
python3 tools/step13_matrix.py "$PWD/tmp/exe-compare/selection-68881" candidate
