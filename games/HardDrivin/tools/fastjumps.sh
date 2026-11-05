#!/bin/bash
# tools/fastjumps.sh PREFIX: jump_clear probes at full throttle, entry speeds 300-420, from the current root
p=$1
specs=""
for v in 300 315 330 345 360 375 390 405 420; do specs="$specs $p-$v:C4_VELOCITY=$v,C4_THROTTLE=100"; done
SCENARIO=jump_clear SUMMARY=jump_pass.py bash tools/probe.sh a500 450 $specs
