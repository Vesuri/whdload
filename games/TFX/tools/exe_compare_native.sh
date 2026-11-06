#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
export DEBUG_PORT=2611 FSUAE="$PWD/tmp/opt20-project-emulator/fs-uae/fs-uae"
export PROFILE_SLAVE="$PWD/tmp/exe-compare/render.slave" DELTA_LISTING="$PWD/tmp/exe-compare/render.lst"
for MACHINE in 030 060 020; do
 export MACHINE
 for test in project gouraud; do
  out="$PWD/tmp/exe-compare/native-$MACHINE-$test"
  if [ ! -f "$out/results.json" ]; then python3 "tools/opt20_${test}_test.py" "$out"; fi
  if [ "$test" = project ]; then python3 tools/check_opt20_project.py "$out"; fi
 done
done
