#!/usr/bin/env bash
# Boot Workbench 2.04 (Kickstart 3.1) and run F1GP-Ed 3.44 on a writable copy of the game's
# f1gp file, for F1's write map (tools/f1_ed.py drives it through DEBUG=1).
#   DATAFILE=path   an F1GP-Ed datafile, loaded at start (DATAFILE=DH0:in.f1gp)
#   GAMEFILE=path   the f1gp file to edit (default the pinned one); the copy is DH1:f1gp
# The f1gp copy, F1GP-Ed and its settings live in .run/ed and are rebuilt on every boot.
set -euo pipefail
cd "$(dirname "$0")"
. ./env.sh
. "$FSUAE_COMMON"

ARCHIVE=../tmp/archives/F1GP-Ed.lha
ED=../tmp/f1ed
GAMEFILE="${GAMEFILE:-../tmp/game/FormulaOneGrandPrix4Disk/data/f1gp}"
WB="${WB:-$WORKBENCH_ADF}"
RUN=.run; DH0="$RUN/ed/dh0"; DH1="$RUN/ed/dh1"

want=$(sed -n 's/^\([0-9a-f]*\)  tmp\/archives\/F1GP-Ed.lha$/\1/p' ../manifest/SHA256SUMS)
if [ ! -f "$ED/F1GP-Ed/F1GP-Ed" ]; then
  [ "$(shasum -a 256 "$ARCHIVE" | cut -d' ' -f1)" = "$want" ] || { echo "ed.sh: $ARCHIVE does not match the manifest" >&2; exit 1; }
  rm -rf "$ED"; mkdir -p "$ED"
  (cd "$ED" && lha xq "$OLDPWD/$ARCHIVE" >/dev/null)
fi

fsuae_prepare
rm -rf "$RUN/ed"
mkdir -p "$DH0/s" "$DH0/Libs" "$DH0/env" "$DH1" "$RUN/state"
cp -R "$ED/F1GP-Ed" "$DH0/F1GP-Ed"
cp -f "$ED/F1GP-Ed/Libs/"*.library "$DH0/Libs/"
cp -f "$GAMEFILE" "$DH1/f1gp"
[ -n "${DATAFILE:-}" ] && cp -f "$DATAFILE" "$DH0/in.f1gp"
chmod -R u+w "$DH0" "$DH1"
args=; [ -n "${DATAFILE:-}" ] && args="DATAFILE=DH0:in.f1gp"
printf '%s\n' 'DF0:C/Assign C: DF0:C' 'Assign LIBS: DF0:Libs' 'Assign LIBS: DH0:Libs ADD' \
  'Assign DEVS: DF0:Devs' 'Assign FONTS: DF0:Fonts' 'Assign L: DF0:L' \
  'MakeDir RAM:ENV RAM:T' 'Assign ENV: RAM:ENV' 'Assign T: RAM:T' 'Assign ENVARC: DH0:env' \
  'Assign f1gp_disk_#2: DH1:' 'Stack 16384' 'FailAt 999' 'CD DH0:F1GP-Ed' \
  "F1GP-Ed $args" > "$DH0/s/startup-sequence"
rm -f "$RUN"/state/*.uss

SHOTS="${FSEMU_SCREENSHOTS_DIR:-$PWD/../tmp/shots}"; mkdir -p "$SHOTS"; export FSEMU_SCREENSHOTS_DIR="$SHOTS"
AMIGA_MODEL="${AMIGA_MODEL:-A500}" CPU="${CPU:-68000}"
CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" SLOW_KB="${SLOW_KB:-1536}"
JOY0="${JOY0:-mouse}" JOY1="${JOY1:-keyboard}"
fsuae_options
fsuae_launch \
  --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  --floppy_drive_0="$WB" \
  --window_width=760 --window_height=568 --state_dir="$RUN/state"
