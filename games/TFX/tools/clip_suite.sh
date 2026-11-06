#!/bin/bash
# Step 3b: native twins, CPU/option gates and the balanced 2,000-field pair, one emulator at a time.
set -u
cd "$(dirname "$0")/.."
D=$PWD;P=$D/tmp/step3
export FSUAE=$D/tmp/opt20-project-emulator/fs-uae/fs-uae PROFILE_SLAVE=$P/clip.slave DELTA_LISTING=$P/clip.lst
rm -rf $P/clip-tests $P/clip-tests-seed
python3 $D/tools/opt20_clip_test.py $P/clip-tests > $P/clip-tests.log 2>&1; echo "twins exit $? $(tail -1 $P/clip-tests.log | cut -c1-300)"
for g in "040 0" "040 0 original" "060 0" "030 0" "040 1"; do
  set -- $g; n=clip-gate-$1-c5$2${3:+-$3}
  CUSTOM5=$2 python3 $D/tools/opt20_gate.py $P/$n $1 ${3:-} > $P/$n.log 2>&1
  echo "$n exit $? $(python3 -c "import json;d=json.load(open('$P/$n/gate.json'));print(d['scan'],d['panel'],d['mask'])" 2>&1 | tail -1)"
done
export PATCH_KIND=scan END_FIELD=2002
CONTROL=1 python3 $D/tools/opt20_balanced_profile.py $P/clip-off > $P/clip-off.log 2>&1; echo "off exit $?"
for k in 1 2 3; do
  TEST_SEED=$P/clip-off-seed MATCH_ENTRY=$P/clip-off python3 $D/tools/opt20_balanced_profile.py $P/clip-on-$k > $P/clip-on-$k.log 2>&1; r=$?
  echo "on-$k exit $r $(cat $P/clip-on-$k/entry-match.json 2>/dev/null)"
  [ $r = 0 ] && break
  grep -q "startup mismatch" $P/clip-on-$k.log || break
done
