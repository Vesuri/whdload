#!/usr/bin/env bash
# Serial mode/input comparisons with W1 off/on on both CPUs. No FPS claim.
set -euo pipefail
cd "$(dirname "$0")/.."
. amiga/env.sh
prefix=${1:-sim-modes-final}
export FSUAE="${FSUAE:-$FSUAE_ARM}"
build="tmp/build-simulation-modes"
make -s -C whdload verify OUT="../$build" VASMFLAGS='-DTIMING_STUDY=1 -DTIMING_MODE_TEST=1'
for machine in a1200 a500; do
  base=0x200000
  machine_args=(AMIGA_MODEL=A1200 "KICKSTART=$KICKSTART_A1200" CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 EXTRA_ARGS=--slow_memory=0)
  if [ "$machine" = a500 ]; then
    base=0xc00000
    machine_args=(AMIGA_MODEL=A500 CPU=68000 CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536)
  fi
  for bits in 126 127; do
    for mode in normal delayed; do
      out="tmp/prof/$prefix-$machine-$bits-$mode"
      mkdir -p "$out"
      cp "$build/LegendsOfValour.Slave" "$out/slave.slave"
      cp "$build/LegendsOfValour.lst" "$out/slave.lst"
      env "${machine_args[@]}" KEEP_SLAVE=1 STATE_ONLY=1 STATE_TICKS=120 TAPE_OPTIONS=2049 "WHD_ARGS=CUSTOM2=$bits" \
        tools/fixed_window.sh "$out" "tools/tapes/timing-modes-$mode.txt"
      python3 tools/check_disabled.py "$out" --base "$base" --custom2 "$bits" --display-timing
    done
    python3 tools/lov_modes_check.py "tmp/prof/$prefix-$machine-$bits-normal" "tmp/prof/$prefix-$machine-$bits-delayed"
  done
done
