#!/usr/bin/env bash
# Boot the installed Formula One Grand Prix (4-disk release) under WHDLoad in FS-UAE.
#   amiga/run.sh            windowed, real speed, with sound
#   DEBUG=1 amiga/run.sh    also open the Barto gdb stub on $DEBUG_PORT (no trigger); silent,
#                           window behind the others (WINDOW=front|none, SOUND=1 to change)
#   SLAVE=path amiga/run.sh run another slave build instead of the installed one
#   WHD_ARGS='CUSTOM1=1'    extra WHDLoad options (CUSTOM1=1 skips the intro)
#   AMIGA_SETUP=name        a named machine (AmigaXDev docs/reference/headless-fsuae.md)
# Host: Kickstart 3.1 + Workbench 2.04 floppy boots DH0, which runs WHDLoad on DH1; the slave
# runs Kickstart 1.3 (kick34005.A500 + .RTB) inside WHDLoad.  DH1 is a disposable copy of the
# pristine extraction, so saves and preferences never reach tmp/game.
# Default machine: the A500-equivalent 512 KB chip + 1.5 MB slow RAM, no fast RAM.
set -euo pipefail
CALLER="$PWD"
cd "$(dirname "$0")"
. ./env.sh
. "$FSUAE_COMMON"

GAME="${GAME:-../tmp/game/FormulaOneGrandPrix4Disk}"
SLAVE_NAME=FormulaOneGrandPrix4Disk.Slave
# KICKSTART, KICK13, RTB, WORKBENCH_ADF and WHDLOAD_BINARY: the shared env.sh.
WB="${WB:-$WORKBENCH_ADF}"
WHD="$WHDLOAD_BINARY"
CPU="${CPU:-68000}"
AMIGA_MODEL="${AMIGA_MODEL:-A500}"
RUN=.run; DH0="$RUN/dh0"; DH1="$RUN/dh1"

[ -f "$GAME/$SLAVE_NAME" ] || { echo "run.sh: no $GAME/$SLAVE_NAME (see docs/development.md)" >&2; exit 1; }
if [ -n "${SLAVE:-}" ]; then
  case "$SLAVE" in /*) ;; *) SLAVE="$CALLER/$SLAVE" ;; esac
  [ -f "$SLAVE" ] || { echo "run.sh: no slave $SLAVE" >&2; exit 1; }
fi

fsuae_prepare
rm -rf "$DH0" "$DH1"
mkdir -p "$DH0/s" "$DH0/devs/Kickstarts" "$RUN/state"
cp -R "$GAME" "$DH1"
cp -f "$WHD" "$DH1/WHDLoad"
[ -n "${SLAVE:-}" ] && cp -f "$SLAVE" "$DH1/$SLAVE_NAME"
cp -f "$KICK13" "$DH0/devs/Kickstarts/kick34005.A500"
cp -f "$RTB" "$DH0/devs/Kickstarts/"
chmod -R u+w "$DH0" "$DH1"
printf 'Expert\nReadDelay=0\n' > "$DH0/s/WHDLoad.prefs"
printf '%s\n' 'DF0:C/Assign C: DF0:C' 'DF0:C/Assign LIBS: DF0:Libs' 'DF0:C/Assign DEVS: DH0:devs' \
  'Stack 16384' 'FailAt 999' 'CD DH1:' \
  "WHDLoad $SLAVE_NAME PRELOAD SPLASHDELAY=0 NOREQ ${WHD_ARGS:-}" > "$DH0/s/startup-sequence"
rm -f "$RUN"/state/*.uss

SHOTS="${FSEMU_SCREENSHOTS_DIR:-$PWD/../tmp/shots}"; mkdir -p "$SHOTS"; export FSEMU_SCREENSHOTS_DIR="$SHOTS"

# Model, memory, sound, window, DEBUG, WARP and the rest: fsuae_options in $FSUAE_COMMON.
CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" SLOW_KB="${SLOW_KB:-1536}"
JOY0="${JOY0:-mouse}" JOY1="${JOY1:-keyboard}"
fsuae_options
fsuae_launch \
  --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  --floppy_drive_0="$WB" \
  --window_width=760 --window_height=568 --state_dir="$RUN/state"
