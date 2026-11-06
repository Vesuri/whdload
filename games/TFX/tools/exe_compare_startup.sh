#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
export DEBUG_PORT=2611 FSUAE="$PWD/tmp/opt20-project-emulator/fs-uae/fs-uae"
export PROFILE_SLAVE="$PWD/tmp/exe-compare/auto.slave"
export STEP13_020_FPU=68882 STEP13_CPUS='040 030 060 020'
python3 tools/step13_startup.py "$PWD/tmp/exe-compare/startup"
unset STEP13_020_FPU
export STEP13_CPUS=020
python3 tools/step13_startup.py "$PWD/tmp/exe-compare/startup-no-fpu"
