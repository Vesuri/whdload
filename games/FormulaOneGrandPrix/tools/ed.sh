#!/usr/bin/env bash
# Boot Workbench 2.04 (Kickstart 3.1) and run F1GP-Ed 3.44 on a writable copy of the game's
# f1gp file, for F1's write map (make ed; tools/f1_ed.py drives it through DEBUG=1).
#   DATAFILE=path   an F1GP-Ed datafile, loaded at start (DATAFILE=DH0:in.f1gp)
#   GAMEFILE=path   the f1gp file to edit (default the pinned one); the copy is DH1:f1gp
#   GAMEDIR=path    the game's data directory (default the pinned one), copied to DH1 with
#                   GAMEFILE over its f1gp: the backdrops (.bkg) F1GP-Ed replaces live there
# Paths are relative to the game directory. F1GP-Ed comes from make unpack
# (tmp/game/F1GP-Ed). common/run.sh only boots WHDLoad, so this launcher uses AmigaXDev's
# fsuae_common.sh directly, in its own run directory (tmp/run/ed/.run, rebuilt on every
# boot) with its own gdb-stub port.
set -euo pipefail
GAME_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$GAME_ROOT/../../common/env.sh"
cd "$GAME_ROOT"

ED=tmp/game/F1GP-Ed
GAMEDIR="${GAMEDIR:-tmp/game/FormulaOneGrandPrix4Disk/data}"
GAMEFILE="${GAMEFILE:-$GAMEDIR/f1gp}"
WB="${WB:-$WORKBENCH_ADF}"
[ -f "$ED/F1GP-Ed" ] || { echo "ed.sh: no $ED/F1GP-Ed: run make unpack ARCHIVES=<directory> first" >&2; exit 1; }
case "$GAMEDIR" in /*) ;; *) GAMEDIR="$GAME_ROOT/$GAMEDIR" ;; esac
case "$GAMEFILE" in /*) ;; *) GAMEFILE="$GAME_ROOT/$GAMEFILE" ;; esac
case "${DATAFILE:-}" in /*|'') ;; *) DATAFILE="$GAME_ROOT/$DATAFILE" ;; esac

mkdir -p tmp/run/ed
cd tmp/run/ed
FSUAE_RUN=.run
. "$FSUAE_COMMON"
DH0="$FSUAE_RUN/dh0"; DH1="$FSUAE_RUN/dh1"

fsuae_prepare
rm -rf "$DH0" "$DH1"
mkdir -p "$DH0/s" "$DH0/Libs" "$DH0/env" "$FSUAE_RUN/state"
cp -R "$GAMEDIR" "$DH1"
cp -R "$GAME_ROOT/$ED" "$DH0/F1GP-Ed"
cp -f "$GAME_ROOT/$ED/Libs/"*.library "$DH0/Libs/"
cp -f "$GAMEFILE" "$DH1/f1gp"
[ -z "${DATAFILE:-}" ] || cp -f "$DATAFILE" "$DH0/in.f1gp"
chmod -R u+w "$DH0" "$DH1"
args=; [ -z "${DATAFILE:-}" ] || args="DATAFILE=DH0:in.f1gp"
printf '%s\n' 'DF0:C/Assign C: DF0:C' 'Assign LIBS: DF0:Libs' 'Assign LIBS: DH0:Libs ADD' \
  'Assign DEVS: DF0:Devs' 'Assign FONTS: DF0:Fonts' 'Assign L: DF0:L' \
  'MakeDir RAM:ENV RAM:T' 'Assign ENV: RAM:ENV' 'Assign T: RAM:T' 'Assign ENVARC: DH0:env' \
  'Assign f1gp_disk_#1: DH1:' 'Assign f1gp_disk_#2: DH1:' 'Assign f1gp_disk_#3: DH1:' \
  'Assign f1gp_disk_#4: DH1:' 'Stack 16384' 'FailAt 999' 'CD DH0:F1GP-Ed' \
  "F1GP-Ed $args" > "$DH0/s/startup-sequence"
rm -f "$FSUAE_RUN"/state/*.uss

SHOTS="${FSEMU_SCREENSHOTS_DIR:-$GAME_ROOT/tmp/shots}"; mkdir -p "$SHOTS"; export FSEMU_SCREENSHOTS_DIR="$SHOTS"
AMIGA_MODEL="${AMIGA_MODEL:-A500}" CPU="${CPU:-68000}"
CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" SLOW_KB="${SLOW_KB:-1536}"
JOY0="${JOY0:-mouse}" JOY1="${JOY1:-keyboard}"
WINDOW_WIDTH="${WINDOW_WIDTH:-760}" WINDOW_HEIGHT="${WINDOW_HEIGHT:-568}"
fsuae_options
fsuae_launch \
  --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  --floppy_drive_0="$WB" --state_dir="$FSUAE_RUN/state"
