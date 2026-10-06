#!/usr/bin/env bash
# A/B a CUSTOM2 performance patch on fixed windows: capture off and on, one at a time, then
# run the full analysis chain on each capture.  Used for the W2 measurements
# (docs/profiling.md); summarise with tools/ab_summary.py PREFIX.
#   tools/ab_window.sh PREFIX OFF_BITS ON_BITS [ROUTES [MACHINES]]
#   e.g. tools/ab_window.sh w2 1 3 "spin wall" "a500 a1200 68000-fast"
# Captures go to tmp/prof/PREFIX-ROUTE-MACHINE-{off,on}; routes are tools/tapes/ROUTE.txt.
# Machines: a500 (A500-equivalent), a1200 (68EC020 + 4 MB fast), 68000-fast (68000 + 8 MB fast).
set -euo pipefail
cd "$(dirname "$0")/.."
PREFIX=$1 OFF_BITS=$2 ON_BITS=$3 ROUTES=${4:-"spin wall"} MACHINES=${5:-"a500 a1200"}
measure() {
  local route=$1 machine=$2 mode=$3 out base bits
  out="tmp/prof/${PREFIX}-${route}-${machine}-${mode}"
  bits=$OFF_BITS; [ "$mode" != on ] || bits=$ON_BITS
  base=0xc00000; [ "$machine" = a500 ] || base=0x200000
  local -a machine_args
  case "$machine" in
    a500) machine_args=(AMIGA_MODEL=A500 CPU=68000 CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536) ;;
    a1200) machine_args=(AMIGA_MODEL=A1200 "KICKSTART=$AMIGA_SHARE/Kickstarts/kick40068.A1200" CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 EXTRA_ARGS=--slow_memory=0) ;;
    68000-fast) machine_args=(AMIGA_MODEL=A500 CPU=68000 CHIP_KB=1024 FAST_KB=8192 EXTRA_ARGS=--slow_memory=0) ;;
    *) echo "unknown machine $machine" >&2; exit 1 ;;
  esac
  env "${machine_args[@]}" TAPE_OPTIONS=1 "WHD_ARGS=CUSTOM2=$bits" tools/fixed_window.sh "$out" "tools/tapes/$route.txt"
  export SLAVE="$PWD/$out/slave.slave"
  if [ "$mode" = off ]; then python3 tools/check_disabled.py "$out" --base "$base" --custom2 "$OFF_BITS"
  else python3 tools/chunky_check.py "$out" --base "$base" --expect auto; fi
  python3 tools/frames.py "$out/trace.bin" "$out/code.bin" "$base" > "$out/frames.txt"
  python3 tools/lov_report.py "$out/trace.bin" "$out/code.bin" --base "$base" > "$out/profile.txt"
  python3 tools/c2p_report.py "$out" --base "$base" > "$out/c2p.txt"
  python3 tools/render_report.py "$out" --base "$base" > "$out/render.txt"
  python3 tools/blocks.py "$out" --base "$base" > "$out/blocks.txt"
  python3 tools/lov_state.py "$out" --base "$base" > "$out/state.json"
  head -4 "$out/frames.txt"
  cat "$out/c2p.txt" "$out/render.txt"
}
for route in $ROUTES; do
  for machine in $MACHINES; do
    for mode in off on; do measure "$route" "$machine" "$mode"; done
  done
done
