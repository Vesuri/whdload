#!/usr/bin/env bash
# Serial native-button and direct-mouse input checks on both reference CPUs.
set -euo pipefail
cd "$(dirname "$0")/.."
. amiga/env.sh
prefix=${1:-mouse-native}
export FSUAE="${FSUAE:-$FSUAE_ARM}"
build=tmp/build-mouse-native
make -s -C whdload verify OUT="../$build" VASMFLAGS='-DTIMING_STUDY=1 -DVERIFY_WAIT_RESCUE=1'
for machine in a1200 a500; do
  base=0x200000
  machine_args=(AMIGA_MODEL=A1200 "KICKSTART=$KICKSTART_A1200" CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 EXTRA_ARGS=--slow_memory=0)
  if [ "$machine" = a500 ]; then
    base=0xc00000
    machine_args=(AMIGA_MODEL=A500 CPU=68000 CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536)
  fi
  for test in hold mouse; do
    out="tmp/prof/$prefix-$machine-$test"
    mkdir -p "$out"
    cp "$build/LegendsOfValour.Slave" "$out/slave.slave"
    cp "$build/LegendsOfValour.lst" "$out/slave.lst"
    ticks=50
    options=8389121  # tape + button pulse + 40-field hold
    tape=tools/tapes/spin.txt
    check=(--hold)
    if [ "$test" = mouse ]; then
      ticks=380
      options=1067521  # tape + input fixture + relative mouse + reverse + unit sweep
      tape=tools/tapes/turning-mouse.txt
      check=(--sweep reverse)
    fi
    env "${machine_args[@]}" KEEP_SLAVE=1 STATE_ONLY=1 STATE_TICKS="$ticks" \
      TAPE_OPTIONS="$options" WHD_ARGS=CUSTOM2=255 tools/fixed_window.sh "$out" "$tape"
    python3 tools/turning_input_check.py "$out" "${check[@]}"
    python3 tools/turning_check.py "$out" --base "$base" --native-buttons-only
  done
done
