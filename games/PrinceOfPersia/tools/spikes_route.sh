#!/bin/bash
# The level-1 spikes route (A500, deterministic warp boot), profiled from the first run key to death.
#   tools/spikes_route.sh OUT                  profile (P: steps traced, ~990 fields)
#   PLAIN=1 tools/spikes_route.sh OUT          same inputs, no tracing (f: instead of P:)
# Boot -> Return x2 (the game starts paused) -> Ctrl-K (keyboard control) -> keypad 6 run right,
# drop to the lower floor, stop on the loose plate and fall with it, keypad 4 run left,
# keypad 8 climb the ledge, keypad 4 run left into the spike pit.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="$1"; P=P; [ "${PLAIN:-0}" = 1 ] && P=f
[ -e "$OUT" ] && { echo "$OUT exists" >&2; exit 1; }
STEPS="f:1100 t:ret:4 f:100 t:ret:4 f:200 d:ctrl t:k:4 u:ctrl f:10
 d:kp6 $P:60 u:kp6 $P:40 d:kp6 $P:80 u:kp6 $P:120 d:kp4 $P:340 u:kp4 $P:10
 d:kp8 $P:110 u:kp8 $P:10 d:kp4 $P:220 u:kp4"
if [ "$P" = P ]; then exec python3 tools/profile_run.py "$OUT" $STEPS; else exec python3 tools/route.py "$OUT" $STEPS s:end; fi
