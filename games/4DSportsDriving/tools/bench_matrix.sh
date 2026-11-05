#!/usr/bin/env bash
# SLAVE (or directory of baseline slaves) OUTPUT_ROOT CELL...
set -euo pipefail
cd "$(dirname "$0")/.."
# Collect already completed cells without repeating their verification set.
if [[ ${1:-} = --collect ]]; then
 shift
 python3 tools/bench_collect.py "$@"
 exit
fi
slave=$1 out=$2; shift 2
for cell in "$@"; do
 selected=$slave
 if [[ -d "$slave" ]]; then
  rate=20; [[ "$cell" = A* ]] && rate=10
  suffix=""; [[ "$cell" = *-fast ]] && suffix=-d3
  selected="$slave/verify-sim${rate}${suffix}.slave"
 fi
 bash tools/bench_cell.sh "$selected" "$cell" "$out/$cell"
done
python3 - "$out" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);rows=[json.loads(f.read_text()) for f in sorted(p.glob('*/bench.json'))];(p/'bench.json').write_text(json.dumps(rows,indent=2)+'\n')
PY
