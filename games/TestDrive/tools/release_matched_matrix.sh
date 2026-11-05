#!/bin/bash
set -euo pipefail
. "$(dirname "$0")/env.sh"
cd "$HARNESS_ROOT"
for preset in a500 a1200 a1200-030; do
 for arm in off on; do
  c2=1; if [ "$arm" = off ]; then c2=0; fi
  python3 tools/release_matched_benchmark.py "matched-$preset-$arm" --preset "$preset" --c2 "$c2" > "tmp/phase11/matched-$preset-$arm.log" 2>&1
 done
done
