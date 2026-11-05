#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/../../common/env.sh"
export SLAVE="$ROOT/tmp/build/verify/Gunship.Slave"
for mode in takeoff hover combat; do
 export WHD_ARGS=CUSTOM2=1
 if [ "$mode" = combat ]; then export WHD_ARGS='CUSTOM2=1 CUSTOM3=1'; fi
 machines="a500-fast a1200-fast a1200-030 a1200-040 a1200-060"
 if [ "$mode" != takeoff ] && [ "${ALL_SCENES:-0}" != 1 ]; then
  machines="a500-fast a1200-060"
 fi
 for MACHINE in $machines; do
  export MACHINE
  if [ "$MACHINE" = a500-fast ]; then
   export INSTRUMENT=barto GUNSHIP_FSUAE="$AMIGA_SHARE/fs-uae-mouse/fs-uae"
  else
   export INSTRUMENT=aprof GUNSHIP_FSUAE="$AMIGA_SHARE/fs-uae-aprof-mouse/fs-uae"
  fi
  python3 "$ROOT/tools/verify_run.py" "$ROOT/tmp/a-final/matrix/$mode/$MACHINE" "$mode"
 done
done
