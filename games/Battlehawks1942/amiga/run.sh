#!/usr/bin/env bash
# Boot the installed original Battlehawks 1942 under WHDLoad in FS-UAE.
#   amiga/run.sh            windowed, real speed, with sound
#   DEBUG=1 amiga/run.sh    also open the Barto gdb stub on $DEBUG_PORT (no trigger); silent,
#                           window behind the others (WINDOW=front|none, SOUND=1 to change)
#   SLAVE=path amiga/run.sh run another slave build instead of the installed one
#   RECORD=file / PLAYBACK=file   record input / replay a recording (both deterministic)
# Host: Kickstart 3.1 + Workbench 2.04 floppy boots DH0, which runs WHDLoad on DH1;
# the slave itself runs Kickstart 1.3 (kick34005.A500 + .RTB) inside WHDLoad, with trackdisk
# reading Disk.1-3 (the game boots from its own AmigaDOS floppy image).
set -euo pipefail
cd "$(dirname "$0")"
. ./env.sh
. "$FSUAE_COMMON"

GAME="${GAME:-../tmp/game/Battlehawks1942}"
# KICKSTART, KICK13, RTB, WORKBENCH_ADF and WHDLOAD_BINARY: the shared env.sh.
WB="${WB:-$WORKBENCH_ADF}"
WHD="$WHDLOAD_BINARY"
CPU="${CPU:-68000}"
AMIGA_MODEL="${AMIGA_MODEL:-A500}"
RUN=.run; DH0="$RUN/dh0"; DH1="$RUN/dh1"

fsuae_claim_port
rm -rf "$DH0" "$DH1"
mkdir -p "$DH0/s" "$DH0/devs/Kickstarts" "$RUN/state"
cp -R "$GAME" "$DH1"
cp -f "$WHD" "$DH1/WHDLoad"
# SLAVE= runs a rebuilt or patched slave in place of the installed one.
[ -n "${SLAVE:-}" ] && cp -f "$SLAVE" "$DH1/Battlehawks1942.Slave"
cp -f "$KICK13" "$DH0/devs/Kickstarts/kick34005.A500"
cp -f "$RTB" "$DH0/devs/Kickstarts/"
chmod -R u+w "$DH0" "$DH1"
printf 'Expert\nReadDelay=0\n' > "$DH0/s/WHDLoad.prefs"
printf '%s\n' 'DF0:C/Assign C: DF0:C' 'DF0:C/Assign LIBS: DF0:Libs' 'DF0:C/Assign DEVS: DH0:devs' \
  'Stack 16384' 'FailAt 999' 'CD DH1:' \
  "WHDLoad Battlehawks1942.Slave PRELOAD SPLASHDELAY=0 NOREQ ${WHD_ARGS:-}" > "$DH0/s/startup-sequence"
rm -f "$RUN"/state/*.uss

# PLAYBACK= replays an input recording (tools/splice_rec.py). FS-UAE appends to the file it
# plays and rewrites it on exit, so it plays a copy.  It takes precedence over RECORD.
PLAY=()
if [ -n "${PLAYBACK:-}" ]; then
  cp -f "$PLAYBACK" "$RUN/playback.rec"
  PLAY=(--record="$PWD/$RUN/playback.rec" --deterministic=1)
fi
SHOTS="${FSEMU_SCREENSHOTS_DIR:-$PWD/$RUN/shots}"; mkdir -p "$SHOTS"; export FSEMU_SCREENSHOTS_DIR="$SHOTS"

# Model, memory, sound, window, DEBUG, RECORD and the rest: fsuae_options in $FSUAE_COMMON.
# JOY0/JOY1=none also set the port's mode to nothing: "none" alone only unplugs the host
# device, and the host mouse still moves the port's counters (JOY0DAT differed between boots).
CHIP_KB="${CHIP_KB:-1024}" FAST_KB="${FAST_KB:-2048}" JOY0="${JOY0:-mouse}" JOY1="${JOY1:-keyboard}"
fsuae_options
fsuae_launch "${PLAY[@]}" \
  --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  --floppy_drive_0="$WB" \
  --window_width=760 --window_height=568 --state_dir="$RUN/state"
