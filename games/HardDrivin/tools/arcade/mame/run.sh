#!/bin/bash
# Run headless MAME harddriv with private directories and a wall-clock limit.
# -video none alone still opens a full-screen window on macOS: SDL's dummy
# video and audio drivers keep MAME away from the window server altogether.
# Usage: run.sh RUN_DIR LUA_SCRIPT WALL_SECONDS [MAME args...]
# The Lua script sees RUN_DIR as HD_RUN. Output goes to RUN_DIR/mame.out.
here=$(cd "$(dirname "$0")" && pwd)
# harddriv.zip, pinned in inputs.sha256, is in the game's tmp/archives/ (make unpack).
archives=$(cd "$here/../../../tmp/archives" && pwd) || exit 1
MAME=${MAME:-mame}
run=$1; lua=$2; wall=$3; shift 3
mkdir -p "$run/cfg" "$run/nvram" "$run/sta" "$run/snap" || exit 1
run=$(cd "$run" && pwd)
case $lua in /*) ;; *) lua=$(pwd)/$lua ;; esac
cd "$run" || exit 1
HD_RUN="$run" SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy gtimeout --signal=TERM --kill-after=10 "$wall" "$MAME" harddriv \
 -rompath "$archives" -noreadconfig -noplugins -homepath "$run" \
 -video none -window -nomaximize -sound none -nothrottle -skip_gameinfo \
 -keyboardprovider none -mouseprovider none -joystickprovider none -lightgunprovider none \
 -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" -state_directory "$run/sta" \
 -snapshot_directory "$run/snap" -autoboot_script "$lua" "$@" >"$run/mame.out" 2>&1 &
pid=$!
echo $pid >"$run/mame.pid"
wait $pid; status=$?
rm -f "$run/mame.pid"
exit $status
