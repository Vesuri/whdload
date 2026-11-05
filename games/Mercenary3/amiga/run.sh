#!/usr/bin/env bash
# Boot the installed original Mercenary 3 under WHDLoad in FS-UAE.
#   amiga/run.sh            windowed, real speed, with sound
#   DEBUG=1 amiga/run.sh    also open the Barto gdb stub on $DEBUG_PORT (no trigger); silent,
#                           window behind the others (WINDOW=front|none, SOUND=1 to change)
#   SLAVE=path amiga/run.sh run another slave build instead of the installed one
#   WHD_SPLASH=1 amiga/run.sh show WHDLoad options and wait for Start
# Host: Kickstart 3.1 boots DH0, which runs WHDLoad on DH1. Host files (KICKSTART,
# WHDLOAD_BINARY) and fsuae_common.sh come from the shared env.sh (amiga/env.sh).
# The default machine is the A500-equivalent: 68000, 512 KB chip, 1.5 MB slow, no fast RAM.
# The slave is a direct (no-OS) loader: it reads the game from Disk.1 into its 512 KB BaseMem
# and jumps in, so no Kickstart image is needed inside WHDLoad.
# FS-UAE screenshots go to the ignored tmp/shots.
set -euo pipefail
# Resolve a relative SLAVE against the caller's directory before changing it.
[ -n "${SLAVE:-}" ] && SLAVE="$(cd "$(dirname "$SLAVE")" && pwd)/$(basename "$SLAVE")"
cd "$(dirname "$0")"
. ./env.sh
[ -r "$KICKSTART" ] || { echo "Kickstart image is unreadable: $KICKSTART" >&2; exit 1; }
. "$FSUAE_COMMON"

GAME="${GAME:-../tmp/game/Mercenary3_v1.2_0356/Mercenary3}"
[ -r "$GAME/Mercenary3.Slave" ] || { echo "Game drawer is missing: $GAME" >&2; exit 1; }
WHD="$WHDLOAD_BINARY"
[ -r "$WHD" ] || { echo "WHDLoad binary is unreadable: $WHD" >&2; exit 1; }
CPU="${CPU:-68000}"
AMIGA_MODEL="${AMIGA_MODEL:-A500}"
RUN=.run; DH0="$RUN/dh0"; DH1="$RUN/dh1"

fsuae_prepare
rm -rf "$DH0" "$DH1"
mkdir -p "$DH0/s" "$RUN/state"
# DH1 is a disposable copy: save games written during a run never reach the pristine drawer.
cp -R "$GAME" "$DH1"
cp -f "$WHD" "$DH1/WHDLoad"
[ -n "${SLAVE:-}" ] && cp -f "$SLAVE" "$DH1/Mercenary3.Slave"
chmod -R u+w "$DH0" "$DH1"
printf 'Expert\nReadDelay=0\n' > "$DH0/s/WHDLoad.prefs"
WHD_UI='SPLASHDELAY=0 NOREQ'
[ "${WHD_SPLASH:-0}" = 1 ] && WHD_UI='SPLASHDELAY=-1'
printf '%s\n' 'Stack 16384' 'FailAt 999' 'CD DH1:' \
  "WHDLoad Mercenary3.Slave CACHE PRELOAD $WHD_UI ${WHD_ARGS:-}" > "$DH0/s/startup-sequence"
rm -f "$RUN"/state/*.uss

SHOTS="${FSEMU_SCREENSHOTS_DIR:-$(cd .. && pwd)/tmp/shots}"; mkdir -p "$SHOTS"; export FSEMU_SCREENSHOTS_DIR="$SHOTS"

# Model, memory, sound, window, DEBUG, RECORD and the rest: fsuae_options in $FSUAE_COMMON.
# JOY0=none also sets port 0's mode to nothing: "none" alone unplugs the host device, but port 0
# stays in mouse mode and the host mouse still moves its counters.
CHIP_KB="${CHIP_KB:-512}" SLOW_KB="${SLOW_KB:-1536}" FAST_KB="${FAST_KB:-0}"
JOY0="${JOY0:-mouse}" JOY1="${JOY1:-keyboard}"
fsuae_options
fsuae_launch \
  --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  --window_width=760 --window_height=568 --state_dir="$RUN/state"
