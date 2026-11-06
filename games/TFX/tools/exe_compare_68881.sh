#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
export DEBUG_PORT=2611 FSUAE="$PWD/tmp/opt20-project-emulator/fs-uae/fs-uae"
export PROFILE_SLAVE="$PWD/tmp/exe-compare/render.slave" DELTA_LISTING="$PWD/tmp/exe-compare/render.lst" PROFILE=0 MACHINE=020 EXTRA_UAE=--uae_fpu_model=68881
for fixture in action follow; do
 export FLIGHT_TAPE="$PWD/tools/flight.tape.json"
 if [ "$fixture" = follow ]; then export FLIGHT_TAPE="$PWD/tools/follow.tape.json"; fi
 for VARIANT in integer newfpu; do
  export VARIANT
  unset AUDIT_RENDER
  if [ "$VARIANT" = newfpu ]; then export AUDIT_RENDER=1; fi
  python3 tools/cpu_profile.py "$PWD/tmp/exe-compare/020-68881-$fixture-$VARIANT"
 done
done
