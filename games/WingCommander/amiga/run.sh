#!/usr/bin/env bash
# Adapted from Legends of Valour; each boot gets fresh drives, never deletes a tree.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -n "${SLAVE:-}" ]; then SLAVE="$(cd "$(dirname "$SLAVE")" && pwd)/$(basename "$SLAVE")"; export SLAVE; fi
cd "$ROOT/amiga"
. ./env.sh
export FSUAE="${FSUAE:-$FSUAE_ARM}"
export FSUAE_RUN="${FSUAE_RUN:-../tmp/run}"
export AMIGA_SETUP="${AMIGA_SETUP:-a1200-fast}"
. "$FSUAE_COMMON"
case "${1:-}" in stop) fsuae_stop_previous; exit ;; esac
# Constrain all emulator products, including shared launcher logs, to ignored scratch.
python3 - "$ROOT" "$FSUAE_RUN" <<'PY'
from pathlib import Path
import sys
root, run = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
if (root/'tmp').resolve() not in run.parents:
    raise SystemExit('FSUAE_RUN must be below this project tmp/')
PY
fsuae_prepare
mkdir -p "$FSUAE_RUN"
BOOT=$(mktemp -d "$FSUAE_RUN/boot.XXXXXX")
python3 "$ROOT/tools/runtime_inputs.py" "$BOOT"
DH0="$BOOT/dh0"; DH1="$BOOT/dh1/WingCommanderCD32"
chmod -R u+w "$DH0" "$DH1"
printf 'Expert\nReadDelay=0\n' > "$DH0/s/WHDLoad.prefs"
printf '%s\n' 'DF0:C/Assign C: DF0:C' 'DF0:C/Assign LIBS: DF0:Libs' 'DF0:C/Assign DEVS: DH0:devs' \
  'Stack 16384' 'FailAt 999' 'CD DH1:' \
  "WHDLoad WingCommanderCD32.Slave PRELOAD SPLASHDELAY=0 NOREQ ${WHD_ARGS:-}" > "$DH0/s/startup-sequence"
mkdir -p "$BOOT/state" "$BOOT/shots"
export FSEMU_SCREENSHOTS_DIR="$PWD/$BOOT/shots"
JOY0="${JOY0:-mouse}" JOY1="${JOY1:-keyboard}"
fsuae_options
fsuae_launch --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  --floppy_drive_0="$WORKBENCH_ADF" --state_dir="$BOOT/state"
