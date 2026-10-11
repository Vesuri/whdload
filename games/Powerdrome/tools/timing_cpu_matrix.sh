#!/usr/bin/env bash
# Bounded 10-second logical-timing comparison, not a throughput benchmark.
# Use a frozen WORLD20 coverage build with fixed seeds and initial-pit sync.
# Phase/result-injection fixtures must be off. REQUIRE_PIT_SYNC=0 diagnoses
# unsynchronized initialization; it does not relax state-comparison checks.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=${1:?new output directory}
INPUT=${2:?frozen coverage slave}
[ ! -e "$OUT" ] || { echo 'Use a new output directory' >&2; exit 1; }
CASE_SET=${CASE_SET:-accelerators}
[[ "$CASE_SET" = accelerators || "$CASE_SET" = baseline || "$CASE_SET" = all ]]
mkdir -p "$OUT"
cp "$INPUT" "$OUT/input.slave"
source amiga/env.sh
baseline_kickstart=$KICKSTART
export FIELDS=500 SWAP_ONLY=1 TIMING_STATE=1 TIMING_EARLY=1 ANCHOR=0xbc7c
export SERVE_WAIT=${SERVE_WAIT:-600}
export COVERAGE_PROBES='0xccee 0xcd2c 0xcd3a 0xcde2 0xcedc 0xd56c 0xd058 0xd9a0'
REQUIRE_PIT_SYNC=${REQUIRE_PIT_SYNC:-1}
[[ "$REQUIRE_PIT_SYNC" = 0 || "$REQUIRE_PIT_SYNC" = 1 ]]
runs=()
if [ -n "${TIMING_REFERENCE:-}" ]; then
 cmp "$TIMING_REFERENCE/slave.slave" "$OUT/input.slave"
 [ -f "$TIMING_REFERENCE/final-code.bin" ]
 runs+=("$TIMING_REFERENCE")
fi
run() {
 local name=$1 cpu=$2 hz=$3 fast=$4 model=${5:-A1200} chip=${6:-2048} ram=${7:-4096} slow=${8:-0}
 local kick=$KICKSTART_A1200 extra="--slow_memory=$slow"
 if [ "$model" = A500 ]; then kick=$baseline_kickstart; fi
 if [ "$hz" != 0 ]; then
  extra+=" --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=$hz --uae_cpu_cycle_exact=true"
 fi
 AMIGA_MODEL="$model" KICKSTART="$kick" CHIP_KB="$chip" FAST_KB="$ram" CPU="$cpu" EXTRA_ARGS="$extra" \
 WHD_ARGS="CUSTOM1=$fast CUSTOM3=1 CUSTOM4=$fast CUSTOM5=9 NoCache" \
 bash tools/fixed_window.sh "$OUT/$name" "$OUT/input.slave" > "$OUT/$name.log" 2>&1
 if [ "$REQUIRE_PIT_SYNC" = 1 ]; then
  python3 tools/check_timing_sync.py --flight-window "$OUT/$name" > "$OUT/$name/sync-check.txt"
 fi
 python3 tools/check_timing_world20.py "$OUT/$name" > "$OUT/$name/world-check.txt"
 python3 tools/check_timing_capacity.py "$OUT/$name" > "$OUT/$name/capacity-check.txt"
 python3 tools/check_timing_integrator.py "$OUT/$name" > "$OUT/$name/integrator-check.txt"
 python3 tools/check_timing_brake.py "$OUT/$name" > "$OUT/$name/brake-check.txt"
 python3 tools/check_timing_joystick.py "$OUT/$name" > "$OUT/$name/joystick-check.txt"
 python3 tools/check_timing_resource.py "$OUT/$name" > "$OUT/$name/resource-check.txt"
 if [ "$fast" = 1 ]; then
  python3 tools/perf_status.py "$OUT/$name" > "$OUT/$name/renderer.json"
 fi
 runs+=("$OUT/$name")
 echo "$name: per-run timing checks passed"
}
if [ "$CASE_SET" != baseline ]; then
 run 030-25-fast 68030 25000000 1
 run 040-25-native 68040-NOMMU 25000000 0
 run 040-25-fast 68040-NOMMU 25000000 1
 run 060-50-native 68060-NOMMU 50000000 0
 run 060-50-fast 68060-NOMMU 50000000 1
fi
if [ "$CASE_SET" != accelerators ]; then
 run a500-native 68000 0 0 A500 512 0 1536
 run 000-fastmem-native 68000 0 0 A500 512 4096 1536
 run 000-fastmem-fast 68000 0 1 A500 512 4096 1536
 run 020-native 68EC020 0 0
 run 020-fast 68EC020 0 1
fi
python3 tools/check_timing_world20.py "${runs[@]}" > "$OUT/world-comparison.txt"
python3 tools/check_timing_order.py "${runs[@]}" > "$OUT/control-comparison.txt"
python3 tools/check_timing_resource.py "${runs[@]}" > "$OUT/resource-comparison.txt"
echo "All ${#runs[@]} bounded CPU/renderer comparisons passed"
