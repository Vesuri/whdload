#!/usr/bin/env bash
# Boot a game under WHDLoad in FS-UAE, on any machine.
#   common/run.sh            build the release slave, boot it on the game's default machine
#   common/run.sh stop       stop this game's (and INSTANCE's) emulator
# Run from inside games/<Game>, or set GAME=<Game>. `make run` in a game directory and
# `make run GAME=<Game>` at the root call this.
#
# What runs:
#   VARIANT=name         which slave of a package with several (default: first of VARIANTS)
#   BUILD=name           build and run that build (release, verify, developer, ...)
#   SLAVE=original       the slave in the pristine installed game, unchanged
#   SLAVE=path           any slave file (relative to where make or this script was started)
#   NOBUILD=1            run the existing build without rebuilding
#   WHD_ARGS='...'       WHDLoad options added after the game's WHD_DEFAULTS
#   COREDUMP=0           do not pass COREDUMP. By default WHDLoad writes a register and memory
#                        dump on every exit; the next boot moves it to tmp/dumps/<time>/
# The machine:
#   SETUP=name           an AmigaXDev named machine: a500, a500-1.5m, a500+, a500-020,
#                        a500+-020, a3000, a1200, a1200-fast, a1200-030, a1200-040, a1200-060
#                        (default: the game's SETUP). SETUP=custom: no named machine, only
#                        the variables below (game.conf's, then the caller's)
#   CPU, CHIP_KB, FAST_KB, SLOW_KB, AMIGA_MODEL, KICKSTART
#                        single settings; given by the caller, they also change a named SETUP
#   NTSC=1, JOY0, JOY1, JOY0_MODE, JOY1_MODE, FSUAE (another emulator binary)
#   WB=0                 boot DH0 without the Workbench floppy (default WB=1). The floppy only
#                        supplies C: and LIBS:, but it changes where the game is loaded
# The launch (AmigaXDev docs/reference/headless-fsuae.md):
#   DEBUG=1, WARP=1, SOUND, WINDOW=front|back|none, RECORD, DETERMINISTIC, EXTRA_ARGS
#   INSTANCE=name        a second emulator of the same game, with its own run directory,
#                        drives and gdb-stub port
#   WAIT=1               stay until the emulator exits
#   VERIFY_EXIT=1        write WHDLoad's result (OK or FAIL) to <run>/.run/dh0/whdload-exit.txt
#
# Every boot copies the pristine installed game (tmp/game/$GAME_DIR) to a fresh drive under
# tmp/run/, so saves and changed preferences never reach the original.
#
# game.sh hooks, each optional:
#   game_prepare             after the machine is chosen (AMIGA_SETUP, empty for custom),
#                            before building: may set SLAVE, BUILD, FSUAE, AMIGA_SETUP, ...
#   game_drives DH0 DH1      after the drives are populated, before the startup-sequence
#   game_setup               after AmigaXDev's fsuae_setup: may edit FSUAE_SETUP_ARGS
#   GAME_FSUAE_ARGS=(...)    extra FS-UAE arguments (set in game.sh or game_prepare)
set -euo pipefail
. "$(dirname "$0")/lib.sh"
load_game

ACTION="${1:-run}"
case "$ACTION" in run|stop) ;; *) die "usage: run.sh [run|stop]" ;; esac
case "${INSTANCE:-}" in *[!a-zA-Z0-9_-]*) die "INSTANCE must be a plain name" ;; esac

# The machine variables the caller set: on a named setup they go to EXTRA_ARGS, which beats
# AMIGA_SETUP. game.conf's machine variables apply only to SETUP=custom.
machine_overrides=""
for v in AMIGA_MODEL CPU CHIP_KB FAST_KB SLOW_KB KICKSTART; do
  eval "val=\${$v:-}"
  if [ -n "$val" ] && user_set "$v"; then machine_overrides="$machine_overrides $v"; fi
done

# Run directory: per game and instance, so each has its own gdb-stub port (AmigaXDev's
# launcher derives it from the directory) and only ever stops its own emulator.
RUN_ROOT="$GAME_ROOT/tmp/run/${INSTANCE:-default}"
mkdir -p "$RUN_ROOT"
[ ! -L "$RUN_ROOT" ] || die "$RUN_ROOT must not be a symlink"

if [ "$ACTION" = stop ]; then
  hook game_stop
  cd "$RUN_ROOT"
  . "$FSUAE_COMMON"
  fsuae_stop_previous
  exit 0
fi

# The machine: a named setup, or none for custom. game_prepare may still change it.
AMIGA_SETUP="${AMIGA_SETUP:-${SETUP:-a500}}"
[ "$AMIGA_SETUP" != custom ] || AMIGA_SETUP=""
export AMIGA_SETUP
hook game_prepare

# The slave.
GAME_PATH="$GAME_ROOT/tmp/game/$GAME_DIR"
[ -d "$GAME_PATH" ] || die "no tmp/game/$GAME_DIR: run make unpack ARCHIVES=<directory> first"
[ -f "$GAME_PATH/$SLAVE_FILE" ] || die "no $SLAVE_FILE in tmp/game/$GAME_DIR (check GAME_DIR and SLAVE_FILE)"
case "${SLAVE:-}" in
  original) RUN_SLAVE="" ;;
  '')
    BUILD="${BUILD:-release}"
    if [ "${NOBUILD:-0}" != 1 ]; then VARIANT="$VARIANT" "$COMMON/build.sh" "$BUILD"; fi
    RUN_SLAVE="$GAME_ROOT/tmp/build/$BUILD/$VARIANT.Slave"
    ;;
  *) RUN_SLAVE="$(caller_path "$SLAVE")" ;;
esac
[ -z "$RUN_SLAVE" ] || [ -f "$RUN_SLAVE" ] || die "no slave $RUN_SLAVE"

cd "$RUN_ROOT"
FSUAE_RUN=.run
. "$FSUAE_COMMON"
FSUAE_CLAIM_STRICT="${FSUAE_CLAIM_STRICT:-0}"
fsuae_prepare

DH0="$FSUAE_RUN/dh0"; DH1="$FSUAE_RUN/dh1"
for target in "$FSUAE_RUN" "$DH0" "$DH1"; do
  [ ! -L "$target" ] || die "$target must not be a symlink"
done
# Keep the previous run's WHDLoad core dump (COREDUMP writes it to PROGDIR:, which is DH1).
dumps=""
for f in "$DH1"/.whdl_*; do
  [ -e "$f" ] || continue
  [ -n "$dumps" ] || { dumps="$GAME_ROOT/tmp/dumps/$(date +%Y%m%d-%H%M%S)"; mkdir -p "$dumps"; }
  mv "$f" "$dumps/"
done
[ -z "$dumps" ] || echo "The previous run's WHDLoad core dump is in $dumps"
rm -rf "$DH0" "$DH1"
mkdir -p "$DH0/s" "$DH0/devs/Kickstarts" "$FSUAE_RUN/state"
cp -R "$GAME_PATH" "$DH1"
cp -f "$WHDLOAD_BINARY" "$DH1/WHDLoad"
[ -z "$RUN_SLAVE" ] || cp -f "$RUN_SLAVE" "$DH1/$SLAVE_FILE"
for kick in ${KICKS:-}; do
  [ -f "$AMIGA_SHARE/Kickstarts/$kick" ] || die "no Kickstart $kick in $AMIGA_SHARE/Kickstarts"
  cp -f "$AMIGA_SHARE/Kickstarts/$kick" "$DH0/devs/Kickstarts/"
  [ ! -f "$AMIGA_SHARE/Kickstarts/$kick.RTB" ] || cp -f "$AMIGA_SHARE/Kickstarts/$kick.RTB" "$DH0/devs/Kickstarts/"
done
chmod -R u+w "$DH0" "$DH1"
hook game_drives "$DH0" "$DH1"
printf 'Expert\nReadDelay=0\n' > "$DH0/s/WHDLoad.prefs"
# Without the floppy DH0 is the boot volume, so DEVS: is DH0:devs; Stack, FailAt and CD are
# shell built-ins.
floppy=()
: > "$DH0/s/startup-sequence"
if [ "${WB:-1}" = 1 ]; then
  floppy=(--floppy_drive_0="$WORKBENCH_ADF")
  printf '%s\n' 'DF0:C/Assign C: DF0:C' 'DF0:C/Assign LIBS: DF0:Libs' 'DF0:C/Assign DEVS: DH0:devs' \
    >> "$DH0/s/startup-sequence"
fi
coredump=" COREDUMP"; [ "${COREDUMP:-1}" = 1 ] || coredump=""
printf '%s\n' 'Stack 16384' 'FailAt 999' 'CD DH1:' \
  "WHDLoad $SLAVE_FILE ${WHD_DEFAULTS-PRELOAD SPLASHDELAY=0 NOREQ}$coredump ${WHD_ARGS:-}" >> "$DH0/s/startup-sequence"
if [ "${VERIFY_EXIT:-0}" = 1 ]; then
  printf '%s\n' 'If WARN' 'Echo "FAIL" >DH0:whdload-exit.txt' 'Else' \
    'Echo "OK" >DH0:whdload-exit.txt' 'EndIf' >> "$DH0/s/startup-sequence"
fi
rm -f "$FSUAE_RUN"/state/*.uss
SHOTS="${FSEMU_SCREENSHOTS_DIR:-$GAME_ROOT/tmp/shots}"; mkdir -p "$SHOTS"; export FSEMU_SCREENSHOTS_DIR="$SHOTS"

# The machine.
if [ -n "$AMIGA_SETUP" ]; then
  for v in $machine_overrides; do
    eval "val=\$$v"
    case "$v" in
      AMIGA_MODEL) EXTRA_ARGS="${EXTRA_ARGS:-} --amiga_model=$val" ;;
      CPU) EXTRA_ARGS="${EXTRA_ARGS:-} --cpu=$val" ;;
      CHIP_KB) EXTRA_ARGS="${EXTRA_ARGS:-} --chip_memory=$val" ;;
      FAST_KB) EXTRA_ARGS="${EXTRA_ARGS:-} --fast_memory=$val" ;;
      SLOW_KB) EXTRA_ARGS="${EXTRA_ARGS:-} --slow_memory=$val" ;;
      KICKSTART) EXTRA_ARGS="${EXTRA_ARGS:-} --kickstart_file=$val" ;;
    esac
  done
  export EXTRA_ARGS="${EXTRA_ARGS:-}"
else
  AMIGA_MODEL="${AMIGA_MODEL:-A500}" CPU="${CPU:-68000}"
  CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" SLOW_KB="${SLOW_KB:-512}"
fi
if has_hook game_setup; then
  eval "$(declare -f fsuae_setup | sed '1s/fsuae_setup/_shared_fsuae_setup/')"
  fsuae_setup() { _shared_fsuae_setup || return 1; game_setup; }
fi
mode_args=()
[ -z "${JOY0_MODE:-}" ] || mode_args+=(--joystick_port_0_mode="$JOY0_MODE")
[ -z "${JOY1_MODE:-}" ] || mode_args+=(--joystick_port_1_mode="$JOY1_MODE")
# Built outside ${FSUAE_TITLE:-...}: the "}" of {machine} would end that expansion early.
title="${TITLE:-$GAME}${INSTANCE:+ ($INSTANCE)} · {machine} · port $DEBUG_PORT"
export FSUAE_TITLE="${FSUAE_TITLE:-$title}"

fsuae_options
fsuae_launch --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  ${floppy[@]+"${floppy[@]}"} --state_dir="$FSUAE_RUN/state" \
  ${mode_args[@]+"${mode_args[@]}"} ${GAME_FSUAE_ARGS[@]+"${GAME_FSUAE_ARGS[@]}"}
if [ "${WAIT:-0}" = 1 ]; then
  while kill -0 "$FSUAE_PID" 2>/dev/null; do sleep 1; done
fi
