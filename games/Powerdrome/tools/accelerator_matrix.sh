#!/usr/bin/env bash
# Sequential uncached accelerator timing checks; never concurrent per repo.
set -euo pipefail
cd "$(dirname "$0")/.."
MODE=${1:?timing}
[ "$MODE" = timing ] || { echo 'Mode must be timing' >&2; exit 1; }
OUT=${2:?new output directory}
INPUT=${3:-tmp/build/Powerdrome-verify.slave}
[ ! -e "$OUT" ] || { echo 'Use a new output directory' >&2; exit 1; }
mkdir -p "$OUT"
cp "$INPUT" "$OUT/input.slave"
source amiga/env.sh
export AMIGA_MODEL=A1200 KICKSTART="$KICKSTART_A1200" CHIP_KB=2048 FAST_KB=4096
export FIELDS=500 SWAP_ONLY=1 CAPTURE_SHOT=1 SERVE_WAIT=${SERVE_WAIT:-600}
run() {
 local name=$1 cpu=$2 hz=$3 options=$4
 CPU="$cpu" EXTRA_ARGS="--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=$hz --uae_cpu_cycle_exact=true" \
 WHD_ARGS="CUSTOM5=2 NoCache $options" tools/fixed_window.sh "$OUT/$name" "$OUT/input.slave" > "$OUT/$name.log" 2>&1
 python3 tools/perf_status.py "$OUT/$name" > "$OUT/$name/renderer.json"
 tail -2 "$OUT/$name.log"
}
export ANCHOR=0xbc7c
run 030-25-off 68030 25000000 'CUSTOM1=0'
run 030-25-on 68030 25000000 'CUSTOM1=1'
run 030-8-on 68030 8000000 'CUSTOM1=1'
run 040-25-off 68040-NOMMU 25000000 'CUSTOM1=0'
run 040-25-on 68040-NOMMU 25000000 'CUSTOM1=1'
run 040-8-on 68040-NOMMU 8000000 'CUSTOM1=1'
run 060-50-off 68060-NOMMU 50000000 'CUSTOM1=0'
run 060-50-on 68060-NOMMU 50000000 'CUSTOM1=1'
run 060-8-on 68060-NOMMU 8000000 'CUSTOM1=1'
