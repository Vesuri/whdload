#!/usr/bin/env bash
# Timing excludes pixel instrumentation; completed pixels use a separate build.
set -euo pipefail
cd "$(dirname "$0")/.."
prefix=${1:?Choose a fresh prefix under tmp/prof}
case "$prefix" in tmp/prof/*) ;; *) echo 'Prefix must be under tmp/prof' >&2; exit 1;; esac
unset ACCEL TWIN PIXELS TAPE_SCENARIO TAPE_DETAIL SLAVE
machine_settings() {
 if [ "$1" = a500 ]; then
  export AMIGA_MODEL=A500 CPU=68000 CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536
  export KICKSTART="${AMIGA_SHARE:-$HOME/.local/share/amiga}/Kickstarts/kick40063.A600"
 else
  export AMIGA_MODEL=A1200 CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 EXTRA_ARGS=--slow_memory=0
  export KICKSTART="${AMIGA_SHARE:-$HOME/.local/share/amiga}/Kickstarts/kick40068.A1200"
 fi
}
VERIFY=1 PERF_MASK=127 tools/build.sh
for machine in a500 020; do
 machine_settings "$machine"
 for option in 0 1; do
  capture="$prefix-$machine-$option"
  export WHD_ARGS="CUSTOM2=$option"
  python3 tools/quick_start.py "$capture" --frame 10
  [ "$option" != 0 ] || python3 tools/check_disabled.py "$capture"
  python3 tools/profile_window.py "$capture"
  python3 tools/display_check.py "$capture" > "$capture/display-check.txt"
  python3 tools/native_cost.py "$capture" > "$capture/native-cost.txt"
  python3 tools/w1_trace.py "$capture" > "$capture/w1-trace.txt"
 done
done
VERIFY=1 PIXELS=1 PERF_MASK=127 tools/build.sh
for machine in a500 020; do
 machine_settings "$machine"
 for option in 0 1; do
  capture="$prefix-pixels-$machine-$option"
  export WHD_ARGS="CUSTOM2=$option"
  python3 tools/quick_start.py "$capture" --frame 10
  python3 tools/draw_pixels.py "$capture" --calls 4 > "$capture/draw-pixels.txt"
 done
 python3 tools/compare_draw_pixels.py "$prefix-pixels-$machine-0" "$prefix-pixels-$machine-1"
 python3 tools/combined_report.py "$prefix" --machine "$machine" \
  --pixel-off "$prefix-pixels-$machine-0" --pixel-on "$prefix-pixels-$machine-1"
done
