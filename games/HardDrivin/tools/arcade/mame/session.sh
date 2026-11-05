#!/bin/bash
# Run one hd.lua session in a fresh run directory.
# Usage: session.sh RUN_DIR PLAN.lua
# Copies the pristine nvram first.
here=$(cd "$(dirname "$0")" && pwd)
arcade=$(cd "$here/../../../tmp/arcade" && pwd)
run=$1; plan=$2
case $plan in /*) ;; *) plan=$(pwd)/$plan ;; esac
rm -rf "$run"; mkdir -p "$run/nvram/harddriv" || exit 1
cp -p "$arcade/mame/pristine/"* "$run/nvram/harddriv/" || exit 1
HD_PLAN="$plan" HD_TOOLS="$here" "$here/run.sh" "$run" "$here/hd.lua" "${HD_WALL:-120}" -seconds_to_run "${HD_SECONDS:-120}"
