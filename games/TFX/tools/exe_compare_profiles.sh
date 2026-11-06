#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
export DEBUG_PORT=2611 FSUAE="$PWD/tmp/opt20-project-emulator/fs-uae/fs-uae"
export PROFILE_SLAVE="$PWD/tmp/exe-compare/render.slave" DELTA_LISTING="$PWD/tmp/exe-compare/render.lst" PROFILE=0
for MACHINE in 030 060 020; do
 export MACHINE
 export EXTRA_UAE=
 if [ "$MACHINE" = 020 ]; then export EXTRA_UAE=--uae_fpu_model=68882; fi
 for fixture in action follow; do
  export FLIGHT_TAPE="$PWD/tools/flight.tape.json"
  if [ "$fixture" = follow ]; then export FLIGHT_TAPE="$PWD/tools/follow.tape.json"; fi
  for VARIANT in integer newfpu; do
   export VARIANT
   out="$PWD/tmp/exe-compare/$MACHINE-$fixture-$VARIANT"
   [ ! -f "$out/counts.json" ] || continue
   unset AUDIT_RENDER
   if [ "$VARIANT" = newfpu ]; then export AUDIT_RENDER=1; fi
   python3 tools/cpu_profile.py "$out"
  done
 done
done
