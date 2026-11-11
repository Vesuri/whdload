#!/usr/bin/env bash
# Boot the release archive's installer in FS-UAE (DEBUG=1; tools/install_check.py drives it).
#   tools/install_run.sh [run|stop]
# DH0 boots with the Workbench 2.04 disk's C:, L:, LIBS: and DEVS:, WHDLoad, RawDIC, Patcher,
# DIC (the install script checks for all four) and Installer 43.3 in C:; DH1 is the release archive (ARCHIVE, default the newest dist/ Ferrari archive)
# unpacked; DH2 the empty target. DF0 is a disk named ff1 (the volume the installer asks
# for) holding the installed SPS 0481 game's data files, made in the run directory: no game
# disk image is pinned, and the installer only copies that disk's files. The
# startup-sequence starts the installer as its icon does (APPNAME FerrariFormulaOne, at
# Average level) with WHDLInstPath (its default target) set to DH2:. Machine: SETUP
# (default a1200).
set -euo pipefail
cd "$(dirname "$0")/.."
. ../../common/env.sh
GAME_ROOT=$PWD
RUN_ROOT="$GAME_ROOT/tmp/run/install"
mkdir -p "$RUN_ROOT"
cd "$RUN_ROOT"
FSUAE_RUN=.run
. "$FSUAE_COMMON"
if [ "${1:-run}" = stop ]; then fsuae_stop_previous; exit 0; fi
ARCHIVE="${ARCHIVE:-$(ls -t "$GAME_ROOT"/../../dist/FerrariFormulaOneEnhanced-*.lha | head -1)}"
[ -f "$ARCHIVE" ] || { echo "no release archive: make dist" >&2; exit 1; }
DATA="$GAME_ROOT/tmp/game/FerrariFormulaOne/data"
[ -d "$DATA" ] || { echo "no tmp/game/FerrariFormulaOne/data: make unpack" >&2; exit 1; }
FSUAE_CLAIM_STRICT=0
fsuae_prepare

DH0="$FSUAE_RUN/dh0"; DH1="$FSUAE_RUN/dh1"; DH2="$FSUAE_RUN/dh2"
rm -rf "$DH0" "$DH1" "$DH2" "$FSUAE_RUN/wb" "$FSUAE_RUN/df0.adf"
mkdir -p "$DH0/s" "$DH0/Prefs/Env-Archive" "$DH1" "$DH2" "$FSUAE_RUN/wb" "$FSUAE_RUN/state"
xdftool "$WORKBENCH_ADF" unpack "$FSUAE_RUN/wb" > /dev/null
for d in C L Libs Devs; do cp -R "$FSUAE_RUN/wb/Workbench2.0/$d" "$DH0/"; done
cp -f "$WHDLOAD/C/WHDLoad" "$WHDLOAD/C/RawDIC" "$WHDLOAD/C/Patcher" "$WHDLOAD/C/DIC" "$INSTALLER43" "$DH0/C/"
(cd "$DH1" && "$LHA" xq "$ARCHIVE")
disk=("$FSUAE_RUN/df0.adf" create + format ff1 ffs)
for f in "$DATA"/*; do disk+=(+ write "$f"); done
xdftool "${disk[@]}" > /dev/null
chmod -R u+w "$DH0" "$DH1" "$FSUAE_RUN/df0.adf"
printf '%s\n' 'Assign C: DH0:C' 'Assign L: DH0:L' 'Assign LIBS: DH0:Libs' 'Assign DEVS: DH0:Devs' \
  'MakeDir RAM:T RAM:ENV' 'Assign T: RAM:T' 'Assign ENV: RAM:ENV' 'Assign ENVARC: DH0:Prefs/Env-Archive' \
  'SetEnv WHDLInstPath DH2:' 'Stack 16384' 'FailAt 999' 'CD DH1:FerrariFormulaOne_Install' \
  'Installer Install APPNAME FerrariFormulaOne MINUSER AVERAGE DEFUSER AVERAGE NOLOG' \
  'Echo "INSTALLER-EXIT" >DH0:installer-exit.txt' > "$DH0/s/startup-sequence"
rm -f "$FSUAE_RUN"/state/*.uss

AMIGA_SETUP="${SETUP:-a1200}"; export AMIGA_SETUP
export FSUAE_TITLE="Ferrari Formula One installer · {machine} · port $DEBUG_PORT"
fsuae_options
fsuae_launch --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  --hard_drive_2="$DH2" --floppy_drive_0="$PWD/$FSUAE_RUN/df0.adf" --writable_floppy_images=0 \
  --state_dir="$FSUAE_RUN/state"
