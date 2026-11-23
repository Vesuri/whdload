#!/bin/bash
# tools/render_check.sh [record] [run options]: the render check (docs/development.md).
# Boots with ENTRY=1, takes tools/sentinel.py's route into landscape 0000, then pans with each
# key of PANS for its number of pan steps, and prints the SHA-256 prefix of the front buffer
# after each step, with the fields the step took. Without "record" it compares the hashes with
# tools/render_check.txt (recorded on the a500) and fails on a difference.
# Run options are common/run.sh's (SETUP=a1200-040 WHD_ARGS=DCACHE INSTANCE=b ...).
set -u
cd "$(dirname "$0")/.."
mode=check; [ "${1-}" = record ] && { mode=record; shift; }
. ../../common/env.sh
export WARP=1 WINDOW=none DETERMINISTIC=1 JOY0=none ENTRY=1 "$@"
inst=${INSTANCE:-default}
out=tmp/render_check/${SETUP:-a500}-$inst; rm -rf "$out"; mkdir -p "$out"
t() { python3 tools/sentinel.py "$@"; }
t serve > "$out/serve.log" 2>&1 &
for i in $(seq 1 120); do t peek 0x58c6e 2 >/dev/null 2>&1 && break; sleep 0.5; done
t route "$PWD/$out/route" > /dev/null || { t quit >/dev/null 2>&1; echo "no server" >&2; exit 1; }
# key (raw) and pan steps: D right, S left, L up, comma down
for p in ${PANS:-22:3 21:3 28:2 38:2}; do
  k=${p%:*} n=${p#*:}
  t hold "$k" > /dev/null
  t strips "$n" "$PWD/$out/$k" | sed "s/^/$k /"
  t release "$k" > /dev/null
  t fields 100 > /dev/null
done > "$out/hashes.txt"
t shot "$PWD/$out/end.png" > /dev/null
t quit > /dev/null
awk '{print $1, $2, $4}' "$out/hashes.txt" > "$out/steps.txt"
if [ $mode = record ]; then cp "$out/steps.txt" tools/render_check.txt; cat "$out/hashes.txt"; exit 0; fi
if diff -u tools/render_check.txt "$out/steps.txt" > "$out/diff.txt"; then
  echo "render check: ${SETUP:-a500} ${WHD_ARGS-} matches ($(awk '{s+=$3} END {print s}' "$out/hashes.txt") fields in pans)"
else
  echo "render check: ${SETUP:-a500} ${WHD_ARGS-} DIFFERS (see $out/diff.txt)"; cat "$out/hashes.txt"; exit 1
fi
