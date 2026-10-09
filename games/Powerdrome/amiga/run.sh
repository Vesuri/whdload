#!/usr/bin/env bash
# Boot the installed original Powerdrome under WHDLoad in FS-UAE.
#   amiga/run.sh            windowed, real speed, with sound
#   DEBUG=1 amiga/run.sh    also open the Barto gdb stub on $DEBUG_PORT (no trigger)
#   SLAVE=path amiga/run.sh run another slave build instead of the installed one
#   WHD_SPLASH=1 amiga/run.sh show WHDLoad options and wait for Start
#   WB=1 amiga/run.sh       also insert the Workbench floppy
# Host: Kickstart 3.1 boots DH0, which runs WHDLoad on DH1. Host files come from
# ~/.local/share/amiga (see env.sh for KICKSTART, WHDLOAD, WHDLOAD_BINARY, WORKBENCH_ADF) and fsuae_common.sh.
# FS-UAE screenshots go to the ignored tmp/shots.
# The original slave boots Disk.1 through a patched Kickstart 1.3 image.
set -euo pipefail
# Resolve a relative SLAVE against the caller's directory before changing it.
[ -n "${SLAVE:-}" ] && SLAVE="$(cd "$(dirname "$SLAVE")" && pwd)/$(basename "$SLAVE")"
cd "$(dirname "$0")"
. ./env.sh
[ -r "$KICKSTART" ] || { echo "Kickstart image is unreadable: $KICKSTART" >&2; exit 1; }
. "${FSUAE_COMMON:-$HOME/.local/share/amiga/fsuae_common.sh}"

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

# joystick_port_0=none unplugs the host device, but port 0 stays in mouse mode and the host mouse
# still moves its counters; also set the mode so nothing feeds JOY0DAT.
JOY0_MODE=(); [ "${JOY0:-mouse}" = none ] && JOY0_MODE=(--joystick_port_0_mode=nothing)
AUDIO=(); [ "${SILENT:-0}" = 1 ] && AUDIO=(--audio_driver=dummy)
DBG=(); [ "${DEBUG:-0}" = 1 ] && DBG=(--remote_debugger=20 --remote_debugger_port="$DEBUG_PORT")
REC=(); [ -n "${RECORD:-}" ] && REC=(--record="$RECORD" --deterministic=1)
[ "${DETERMINISTIC:-0}" = 1 ] && REC+=(--deterministic=1)
SHOTS="${FSEMU_SCREENSHOTS_DIR:-$(cd .. && pwd)/tmp/shots}"; mkdir -p "$SHOTS"; export FSEMU_SCREENSHOTS_DIR="$SHOTS"

"${FSUAE:-fs-uae}" \
  --base_dir="$PWD/$RUN/fsuae" \
  --amiga_model="$AMIGA_MODEL" --cpu="$CPU" --chip_memory="${CHIP_KB:-512}" --fast_memory="${FAST_KB:-0}" \
  --kickstart_file="$KICKSTART" \
  --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  ${FLOPPY[@]+"${FLOPPY[@]}"} \
  --joystick_port_0="${JOY0:-mouse}" ${JOY0_MODE[@]+"${JOY0_MODE[@]}"} --joystick_port_1="${JOY1:-keyboard}" \
  --automatic_input_grab=0 --fullscreen=0 --window_width=760 --window_height=568 \
  --ntsc_mode=0 --warp_mode="${WARP:-0}" --state_dir="$RUN/state" \
  "${AUDIO[@]}" "${DBG[@]}" "${REC[@]}" ${EXTRA_ARGS:---slow_memory=1536} > "$RUN/fsuae.log" 2>&1 &
FSUAE_PID=$!; fsuae_track "$FSUAE_PID"
echo "fs-uae pid $FSUAE_PID (log $RUN/fsuae.log, port $DEBUG_PORT)"
