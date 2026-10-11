#!/usr/bin/env bash
# Boot the installed original Stellar 7 under WHDLoad in FS-UAE.
#   amiga/run.sh            windowed, real speed, with sound
#   DEBUG=1 amiga/run.sh    also open the Barto gdb stub on $DEBUG_PORT (no trigger)
#   SOUND=0|1               sound off/on (default: off for DEBUG=1 or warp runs; SILENT=1 = off)
#   JOY0=none amiga/run.sh  leave port 0 empty (the host mouse otherwise injects input)
#   WINDOW=back|none        keep the window behind others / run headless (default: back for
#                           DEBUG=1 or warp runs, front otherwise)
#   SLAVE=path amiga/run.sh run another slave build instead of the installed one
# Shared files (amiga/env.sh; each variable overrides): KICKSTART, KICK13, RTB, WORKBENCH_ADF,
# WHDLOAD_BINARY.
# Host: Kickstart 3.1 + Workbench 2.04 floppy boots DH0, which runs WHDLoad on DH1;
# the slave itself runs Kickstart 1.3 (kick34005.A500 + .RTB) inside WHDLoad.
set -euo pipefail
if [ -n "${SLAVE:-}" ]; then
  case "$SLAVE" in /*) ;; *) SLAVE="$PWD/$SLAVE" ;; esac
fi
cd "$(dirname "$0")"
. ./env.sh
. "${FSUAE_COMMON:-$HOME/.local/share/amiga/fsuae_common.sh}"

GAME="${GAME:-../tmp/game/Stellar7NTSC}"
WB="$WORKBENCH_ADF"
WHD="$WHDLOAD_BINARY"
CPU="${CPU:-68000}"
AMIGA_MODEL="${AMIGA_MODEL:-A500}"
NTSC_MODE="${NTSC_MODE:-1}"
case "$NTSC_MODE" in
  0) UAE_NTSC=false ;;
  1) UAE_NTSC=true ;;
  *) echo "NTSC_MODE must be 0 (PAL) or 1 (NTSC)." >&2; exit 1 ;;
esac
RUN=.run; DH0="$RUN/dh0"; DH1="$RUN/dh1"

# Fail on a occupied port rather than risk another project's emulator.
fsuae_stop_previous
if lsof -nP -iTCP:"$DEBUG_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Debugger port $DEBUG_PORT is occupied; choose DEBUG_PORT explicitly." >&2
  exit 1
fi
for f in "$KICKSTART" "$KICK13" "$RTB" "$WB" "$WHD" "$GAME/Stellar7NTSC.Slave"; do
  [ -f "$f" ] || { echo "Missing required input: $f" >&2; exit 1; }
done
rm -rf "$DH0" "$DH1"
mkdir -p "$DH0/s" "$DH0/devs/Kickstarts" "$RUN/state"
cp -R "$GAME" "$DH1"
cp -f "$WHD" "$DH1/WHDLoad"
# SLAVE= runs a rebuilt or patched slave in place of the installed one.
[ -n "${SLAVE:-}" ] && cp -f "$SLAVE" "$DH1/Stellar7NTSC.Slave"
cp -f "$KICK13" "$DH0/devs/Kickstarts/kick34005.A500"
cp -f "$RTB" "$DH0/devs/Kickstarts/"
chmod -R u+w "$DH0" "$DH1"
printf 'Expert\nReadDelay=0\n' > "$DH0/s/WHDLoad.prefs"
printf '%s\n' 'DF0:C/Assign C: DF0:C' 'DF0:C/Assign LIBS: DF0:Libs' 'DF0:C/Assign DEVS: DH0:devs' \
  'Stack 16384' 'FailAt 999' 'CD DH1:' \
  "WHDLoad Stellar7NTSC.Slave PRELOAD SPLASHDELAY=0 NOREQ ${WHD_ARGS:-}" > "$DH0/s/startup-sequence"
rm -f "$RUN"/state/*.uss

SHOTS="${FSEMU_SCREENSHOTS_DIR:-$PWD/$RUN/shots}"; mkdir -p "$SHOTS"; export FSEMU_SCREENSHOTS_DIR="$SHOTS"

# The shared launcher (fsuae_common.sh) builds the common options from these: debug and warp
# runs are silent and open behind the active window (SOUND=, WINDOW=front|back|none override).
# Slow memory comes from the EXTRA_ARGS default, which the tools set explicitly.
CHIP_KB="${CHIP_KB:-512}"; FAST_KB="${FAST_KB:-0}"
JOY0="${JOY0:-mouse}"; JOY1="${JOY1:-keyboard}"
NTSC="$NTSC_MODE"
EXTRA_ARGS="${EXTRA_ARGS:---slow_memory=1536}"
fsuae_options
fsuae_launch \
  --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  --floppy_drive_0="$WB" --window_width=760 --window_height=568 \
  --uae_ntsc="$UAE_NTSC" --state_dir="$RUN/state"
