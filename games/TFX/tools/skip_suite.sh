#!/bin/bash
# Step 3b whole-call skip: native twins, CPU/option gates, controlled scenes and the
# clock-normalized balanced 2,000-field pair, one emulator at a time.
set -u
cd "$(dirname "$0")/.."
D=$PWD;P=$D/tmp/step3
export FSUAE=$D/tmp/opt20-project-emulator/fs-uae/fs-uae PROFILE_SLAVE=$P/skip.slave DELTA_LISTING=$P/skip.lst
rm -rf $P/skip-tests $P/skip-tests-seed
SKIP=1 python3 $D/tools/opt20_clip_test.py $P/skip-tests > $P/skip-tests.log 2>&1; r=$?; echo "twins exit $r $(tail -1 $P/skip-tests.log | cut -c1-400)"; [ $r = 0 ] || exit 1
for g in "040 0" "040 0 original" "060 0" "030 0" "040 1"; do
  set -- $g; n=skip-gate-$1-c5$2${3:+-$3}
  CUSTOM5=$2 python3 $D/tools/opt20_gate.py $P/$n $1 ${3:-} > $P/$n.log 2>&1
  echo "$n exit $? $(python3 -c "import json;d=json.load(open('$P/$n/gate.json'));print(d['scan'],d['panel'],d['mask'])" 2>&1 | tail -1)"
done
SLAVE_NAME=skip TAG=skip $D/tools/clip_scenes.sh
export CLOCK_NORMALIZE=1 EXTRA_UAE='--uae_rtc=none' PATCH_KIND=scan END_FIELD=2002
CONTROL=1 python3 $D/tools/opt20_balanced_profile.py $P/skip-off > $P/skip-off.log 2>&1; echo "off exit $? $(tail -1 $P/skip-off.log)"
for k in 1 2 3 4 5 6 7 8; do
  TEST_SEED=$P/skip-off-seed MATCH_ENTRY=$P/skip-off python3 $D/tools/opt20_balanced_profile.py $P/skip-on-$k > $P/skip-on-$k.log 2>&1; r=$?
  echo "on-$k exit $r $(cat $P/skip-on-$k/entry-match.json 2>/dev/null) $(tail -1 $P/skip-on-$k.log)"
  [ $r = 0 ] && break
  grep -q "startup mismatch" $P/skip-on-$k.log || break
done
