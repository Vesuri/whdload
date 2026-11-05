#!/usr/bin/env bash
# Boot the installed original Powerdrome under WHDLoad in FS-UAE.
#   amiga/run.sh            windowed, real speed, with sound
#   DEBUG=1 amiga/run.sh    also open the Barto gdb stub on $DEBUG_PORT (no trigger); silent,
#                           window behind the others (WINDOW=front|none, SOUND=1 to change)
#   SLAVE=path amiga/run.sh run another slave build instead of the installed one
#   WHD_SPLASH=1 amiga/run.sh show WHDLoad options and wait for Start
#   WB=1 amiga/run.sh       also insert the Workbench floppy
# Host: Kickstart 3.1 boots DH0, which runs WHDLoad on DH1. Host files come from the shared
# environment (env.sh: KICKSTART, WHDLOAD, WHDLOAD_BINARY, WORKBENCH_ADF) and fsuae_common.sh.
# FS-UAE screenshots go to the ignored tmp/shots.
# The original slave boots Disk.1 through a patched Kickstart 1.3 image.
set -euo pipefail
# Resolve a relative SLAVE against the caller's directory before changing it.
[ -n "${SLAVE:-}" ] && SLAVE="$(cd "$(dirname "$SLAVE")" && pwd)/$(basename "$SLAVE")"
cd "$(dirname "$0")"
. ./env.sh
[ -r "$KICKSTART" ] || { echo "Kickstart image is unreadable: $KICKSTART" >&2; exit 1; }
. "$FSUAE_COMMON"

GAME="${GAME:-../tmp/game/Powerdrome}"
WHD="$WHDLOAD_BINARY"
[ -r "$WHD" ] || { echo "WHDLoad binary is unreadable: $WHD" >&2; exit 1; }
CPU="${CPU:-68000}"
AMIGA_MODEL="${AMIGA_MODEL:-A500}"
RUN=.run; DH0="$RUN/dh0"; DH1="$RUN/dh1"

fsuae_claim_port
rm -rf "$DH0" "$DH1"
mkdir -p "$DH0/s" "$DH0/devs/Kickstarts" "$RUN/state"
cp -R "$GAME" "$DH1"
cp -f "$WHD" "$DH1/WHDLoad"
# SLAVE= runs a rebuilt or patched slave in place of the installed one.
[ -n "${SLAVE:-}" ] && cp -f "$SLAVE" "$DH1/Powerdrome.Slave"
[ -r "$KICK13" ] && [ -r "$RTB" ] || { echo "Kickstart 1.3 or RTB missing" >&2; exit 1; }
cp "$KICK13" "$DH0/devs/Kickstarts/kick34005.A500"
cp "$RTB" "$DH0/devs/Kickstarts/kick34005.A500.RTB"
chmod -R u+w "$DH0" "$DH1"
printf 'Expert\nReadDelay=0\n' > "$DH0/s/WHDLoad.prefs"
# WB=1 adds the WORKBENCH_ADF floppy, which only supplies Assign. The default boots DH0 without
# it (Stack, FailAt and CD are shell built-ins); the floppy moves the load address.
FLOPPY=(); ASSIGNS=()
if [ "${WB:-1}" = 1 ]; then
  [ -r "$WORKBENCH_ADF" ] || { echo "Workbench ADF is unreadable: $WORKBENCH_ADF" >&2; exit 1; }
  FLOPPY=(--floppy_drive_0="$WORKBENCH_ADF")
  ASSIGNS=('DF0:C/Assign C: DF0:C' 'DF0:C/Assign LIBS: DF0:Libs' 'DF0:C/Assign DEVS: DH0:devs')
fi
WHD_UI='SPLASHDELAY=0 NOREQ'
[ "${WHD_SPLASH:-0}" = 1 ] && WHD_UI='SPLASHDELAY=-1'
printf '%s\n' ${ASSIGNS[@]+"${ASSIGNS[@]}"} 'Stack 16384' 'FailAt 999' 'CD DH1:' \
  "WHDLoad Powerdrome.Slave PRELOAD $WHD_UI ${WHD_ARGS:-}" > "$DH0/s/startup-sequence"
rm -f "$RUN"/state/*.uss

SHOTS="${FSEMU_SCREENSHOTS_DIR:-$(cd .. && pwd)/tmp/shots}"; mkdir -p "$SHOTS"; export FSEMU_SCREENSHOTS_DIR="$SHOTS"

# Model, memory, sound, window, DEBUG, RECORD and the rest: fsuae_options in $FSUAE_COMMON
# (JOY0/JOY1=none also unplug the port's mode, so the host mouse feeds nothing).  Slow memory
# defaults to 1.5 MB unless EXTRA_ARGS is given.
CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" JOY0="${JOY0:-mouse}" JOY1="${JOY1:-keyboard}"
[ -n "${EXTRA_ARGS:-}" ] || SLOW_KB="${SLOW_KB:-1536}"
fsuae_options
fsuae_launch \
  --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  ${FLOPPY[@]+"${FLOPPY[@]}"} \
  --window_width=760 --window_height=568 --state_dir="$RUN/state"
