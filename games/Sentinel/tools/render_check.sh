#!/bin/bash
# tools/render_check.sh [record] [run options]: the render check (docs/development.md).
# Boots with ENTRY=1, takes tools/sentinel.py's route into landscape 0000, then pans with each
# key of PANS for its number of pan steps, and prints the SHA-256 prefix of the front buffer
# after each step, with the fields the step took; then the same pans with the pointer at the
# screen edges. Without "record" it compares both sets of hashes with tools/render_check.txt
# (recorded on the a500) and fails on a difference.
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
# the same pans with the pointer at the screen edge (the left button enters pointer mode);
# a step's picture depends on the steps before it, so these have their own lines (p22 ...)
t click > /dev/null; t fields 10 > /dev/null
for p in ${PANS:-22:3 21:3 28:2 38:2}; do
  k=${p%:*} n=${p#*:}
  case $k in 22) e="9999 1536";; 21) e="0 1536";; 28) e="1280 9999";; 38) e="1280 0";; esac
  t pointer $e > /dev/null
  t strips "$n" "$PWD/$out/p$k" | sed "s/^/$k /"
  t pointer 1280 1536 > /dev/null
  t fields 100 > /dev/null
done > "$out/pointer.txt"
t shot "$PWD/$out/end.png" > /dev/null
t quit > /dev/null
{ awk '{print $1, $2, $4}' "$out/hashes.txt"; awk '{print "p" $1, $2, $4}' "$out/pointer.txt"; } > "$out/steps.txt"
if [ $mode = record ]; then cp "$out/steps.txt" tools/render_check.txt; cat "$out/hashes.txt" "$out/pointer.txt"; exit 0; fi
fields() { awk '{s+=$3} END {print s}' "$1"; }
if diff -u tools/render_check.txt "$out/steps.txt" > "$out/diff.txt"; then
  echo "render check: ${SETUP:-a500} ${WHD_ARGS-} matches ($(fields "$out/hashes.txt") fields in key pans, $(fields "$out/pointer.txt") in pointer pans)"
else
  echo "render check: ${SETUP:-a500} ${WHD_ARGS-} DIFFERS (see $out/diff.txt)"; cat "$out/hashes.txt" "$out/pointer.txt"; exit 1
fi
