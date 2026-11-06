#!/usr/bin/env bash
# Sequential cold boots; each cell retains logs and any failure for diagnosis.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
RESULT="${1:?Pass a new output root relative to the game directory (e.g. tmp/step4-matrix)}"
export FSUAE="${FSUAE:-$REPO/tmp/step4-emulator/fs-uae/fs-uae}"
test -x "$FSUAE"
[ ! -e "$RESULT" ] || { echo "Output already exists" >&2; exit 1; }
mkdir -p "$RESULT"
cp tools/run_baseline_matrix.sh "$RESULT/"
for machine in 040 020; do
  for variant in integer original newfpu fpu beta; do
    if [ "$machine" = 020 ] && [ "$variant" != integer ] && [ "$variant" != newfpu ]; then continue; fi
    extra=''
    if [ "$machine" = 040 ]; then extra='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true'; fi
    for repeat in 1 2; do
      cell="$machine-$variant-$repeat"
      if ! python3 tools/baseline_matrix.py --machine "$machine" --variant "$variant" --output "$RESULT/$cell" --seed "$RESULT/seed-$variant" --extra-args="$extra" > "$RESULT/$cell.log" 2>&1; then
        echo "$cell FAILED (see log)"
        break
      fi
      tail -1 "$RESULT/$cell.log"
    done
  done
done
