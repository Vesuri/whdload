#!/usr/bin/env bash
# Adapted from Legends of Valour; each boot gets fresh drives, never deletes a tree.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -n "${SLAVE:-}" ]; then SLAVE="$(cd "$(dirname "$SLAVE")" && pwd)/$(basename "$SLAVE")"; export SLAVE; fi
cd "$ROOT/amiga"
. ./env.sh
export FSUAE="${FSUAE:-$FSUAE_ARM}"
FSUAE_RUN="${FSUAE_RUN:-../tmp/run}"
# The shared launcher expects a path relative to amiga/. Canonicalise overrides
# before it constructs its pid/log paths, and reject symlink escapes from tmp/.
FSUAE_RUN="$(python3 - "$ROOT" "$FSUAE_RUN" <<'PYRUN'
from pathlib import Path
import os, sys
root, run = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
if (root/'tmp').resolve() not in run.parents:
    raise SystemExit('FSUAE_RUN must be below this project tmp/')
print(os.path.relpath(run, Path.cwd()))
PYRUN
)"
export FSUAE_RUN
export AMIGA_SETUP="${AMIGA_SETUP:-a1200-fast}"
. "$FSUAE_COMMON"
# A pidfile alone is insufficient if a PID was reused by another project's UAE.
if [ -f "$FSUAE_PIDFILE" ]; then
  tracked=$(cat "$FSUAE_PIDFILE")
  if fsuae_is_a "$tracked" fs-uae && ! fsuae_is_ours "$tracked"; then
    echo "recorded emulator belongs to another directory; refusing to stop it" >&2
    exit 1
  fi
fi
case "${1:-}" in stop) fsuae_stop_previous; exit ;; esac
FSUAE_CLAIM_STRICT=1
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
