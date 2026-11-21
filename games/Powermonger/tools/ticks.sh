#!/usr/bin/env bash
# Sample the world-tick counter ($535ba) and the game's field counter ($3b796) of a running
# `make serve`, every SECONDS (default 5) host seconds, N times (default 3). Only the field
# counts are emulated time: a warp run covers more fields per host second.
# Prints ticks, fields, fields per tick, and frames drawn ($f8, counted by the quick build with
# CUSTOM4) and frames per second (PAL) for each interval.
set -euo pipefail
cd "$(dirname "$0")/.."
secs="${1:-5}" n="${2:-3}"
rd() { make -s server CMD="gdb x/1wx $1" 2>/dev/null | awk '/^0x[0-9a-f]*:/ {print $2}' | { read -r v; echo $((v)); }; }
t0=$(rd 0x535ba); f0=$(rd 0x3b796); d0=$(rd 0xf8)
for _ in $(seq "$n"); do
  make -s server CMD="wait $secs" >/dev/null 2>&1
  t1=$(rd 0x535ba); f1=$(rd 0x3b796); d1=$(rd 0xf8)
  LC_ALL=C awk -v t=$((t1 - t0)) -v f=$((f1 - f0)) -v d=$((d1 - d0)) 'BEGIN { printf "ticks %d fields %d fields/tick %.2f draws %d fps %.1f\n", t, f, (t ? f / t : 0), d, d * 50 / f }'
  t0=$t1; f0=$f1; d0=$d1
done
