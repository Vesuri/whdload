#!/bin/bash
# Step 1 activation gates: CPU x CUSTOM1/CUSTOM5/original rendering, one emulator at a time.
set -u
cd "$(dirname "$0")/.."
D=$PWD
export FSUAE=$D/tmp/opt20-project-emulator/fs-uae/fs-uae PROFILE_SLAVE=$D/tmp/prof20/intproj.slave DELTA_LISTING=$D/tmp/prof20/intproj.lst
for g in "040 1 0" "040 0 0" "040 1 0 original" "060 1 0" "030 1 0" "040 1 1"; do
  set -- $g
  n=intproj-gate-$1-c1$2-c5$3${4:+-$4}
  CUSTOM1=$2 CUSTOM5=$3 python3 $D/tools/opt20_gate.py $D/tmp/prof20/$n $1 ${4:-} > $D/tmp/prof20/$n.log 2>&1
  echo "$n exit $? $(python3 -c "import json;d=json.load(open('$D/tmp/prof20/$n/gate.json'));print(d['project'],d['mask'],d['exp'])" 2>&1 | tail -1)"
done
