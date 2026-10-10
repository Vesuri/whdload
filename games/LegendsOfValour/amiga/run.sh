#!/usr/bin/env bash
# Boot Legends of Valour under WHDLoad in FS-UAE (local performance prefs optional).
#   amiga/run.sh            windowed, real speed, with sound
#   FSUAE_RUN=dir         run directory under amiga/ (default .run; the debugger tools use .cap,
#                         so captures never stop an interactive session)
#   DEBUG=1 amiga/run.sh    also open the Barto gdb stub on $DEBUG_PORT (no trigger); silent,
#                           window behind the others (WINDOW=front|none, SOUND=1 to change)
#   SLAVE=path amiga/run.sh run another slave build instead of the installed one
#   TAPE=file WHD_ARGS=CUSTOM5=1  scripted mouse input (VERIFY slave, tools/tape.py)
# Host: Kickstart 3.1 + Workbench 2.04 floppy boots DH0, which runs WHDLoad on DH1;
# the slave itself runs Kickstart 1.3 (kick34005.A500 + .RTB) inside WHDLoad.
# Shared ROM, floppy and WHDLoad paths and their overrides: amiga/env.sh.
set -euo pipefail
cd "$(dirname "$0")"
. ./env.sh
# Optional local preference; captures provide explicit SLAVE/WHD_ARGS and override it.
[ ! -f performance.env ] || . ./performance.env
if [ -z "${SLAVE:-}" ] && [ "${LOV_PERFORMANCE_BITS:-0}" != 0 ]; then
  make -s -C ../whdload OUT=../tmp/build-release > /dev/null
  SLAVE="$PWD/../tmp/build-release/LegendsOfValour.Slave"
fi
if [ -z "${WHD_ARGS:-}" ] && [ "${LOV_PERFORMANCE_BITS:-0}" != 0 ]; then
  WHD_ARGS="CUSTOM2=$LOV_PERFORMANCE_BITS"
fi
. "$FSUAE_COMMON"

GAME="${GAME:-../tmp/game/LegendsOfValour}"
CPU="${CPU:-68000}"
AMIGA_MODEL="${AMIGA_MODEL:-A500}"
RUN="$FSUAE_RUN"; DH0="$RUN/dh0"; DH1="$RUN/dh1"

fsuae_claim_port
rm -rf "$DH0" "$DH1"
mkdir -p "$DH0/s" "$DH0/devs/Kickstarts" "$RUN/state"
cp -R "$GAME" "$DH1"
cp -f "$WHDLOAD_BINARY" "$DH1/WHDLoad"
# SLAVE= runs a rebuilt or patched slave in place of the installed one.
[ -n "${SLAVE:-}" ] && cp -f "$SLAVE" "$DH1/LegendsOfValour.Slave"
# TAPE= installs a VERIFY slave input tape (tools/tape.py; read with WHD_ARGS=CUSTOM5=1).
[ -n "${TAPE:-}" ] && cp -f "$TAPE" "$DH1/data/lovtape"
cp -f "$KICK13" "$DH0/devs/Kickstarts/"
cp -f "$RTB" "$DH0/devs/Kickstarts/"
chmod -R u+w "$DH0" "$DH1"
printf 'Expert\nReadDelay=0\n' > "$DH0/s/WHDLoad.prefs"
printf '%s\n' 'DF0:C/Assign C: DF0:C' 'DF0:C/Assign LIBS: DF0:Libs' 'DF0:C/Assign DEVS: DH0:devs' \
  'Stack 16384' 'FailAt 999' 'CD DH1:' \
  "WHDLoad LegendsOfValour.Slave PRELOAD SPLASHDELAY=0 NOREQ ${WHD_ARGS:-}" > "$DH0/s/startup-sequence"
rm -f "$RUN"/state/*.uss

SHOTS="${FSEMU_SCREENSHOTS_DIR:-$PWD/$RUN/shots}"; mkdir -p "$SHOTS"; export FSEMU_SCREENSHOTS_DIR="$SHOTS"

# Model, memory, sound, window, DEBUG, RECORD and the rest: fsuae_options in $FSUAE_COMMON.
CHIP_KB="${CHIP_KB:-1024}" FAST_KB="${FAST_KB:-8192}" JOY0="${JOY0:-mouse}" JOY1="${JOY1:-keyboard}"
fsuae_options
fsuae_launch \
  --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  --floppy_drive_0="$WORKBENCH_ADF" \
  --window_width=760 --window_height=568 --state_dir="$RUN/state"
