#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/../../common/env.sh"
export SLAVE="$ROOT/tmp/build/verify/Gunship.Slave" WHD_ARGS=CUSTOM2=1
for MACHINE in a500-fast a1200-fast a1200-030 a1200-040 a1200-060; do
 export MACHINE
 if [ "$MACHINE" = a500-fast ]; then
  export INSTRUMENT=barto GUNSHIP_FSUAE="$AMIGA_SHARE/fs-uae-mouse/fs-uae"
 else
  export INSTRUMENT=aprof GUNSHIP_FSUAE="$AMIGA_SHARE/fs-uae-aprof-mouse/fs-uae"
 fi
 python3 "$ROOT/tools/verify_run.py" "$ROOT/tmp/a2/matrix/$MACHINE" takeoff
 done
