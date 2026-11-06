#!/bin/bash
# Step 8 (DoRotPt0 delta table): native twins, CPU/option gates, controlled scenes
# with the original routine, and the clock-normalized balanced 2,000-field pair.
set -u
cd "$(dirname "$0")/.."
D=$PWD;P=$D/tmp/rot8
export DEBUG_PORT=${DEBUG_PORT:-2611} FSUAE=$D/tmp/opt20-project-emulator/fs-uae/fs-uae PROFILE_SLAVE=$P/rot.slave DELTA_LISTING=$P/rot.lst
if [ -z "${LATE_ONLY:-}" ]; then
rm -rf $P/rot-tests $P/rot-tests-seed
(cd $D/tools && python3 opt20_rot_test.py $P/rot-tests) > $P/rot-tests.log 2>&1
r=$?; echo "twins exit $r $(tail -2 $P/rot-tests.log | tr '\n' ' ' | cut -c1-300)"; [ $r = 0 ] || exit 1
for g in "040 0" "040 0 original" "060 0" "030 0" "040 1"; do
  set -- $g; n=rot-gate-$1-c5$2${3:+-$3}
  CUSTOM5=$2 python3 $D/tools/opt20_gate.py $P/$n $1 ${3:-} > $P/$n.log 2>&1; echo "$n exit $?"
done
fi
export SCENE_NOMMU=1
for mode in off on; do
  off=; [ $mode = off ] && off=1
  ROT_OFF=$off SCENE_SWAPS=400 python3 $D/tools/opt20_scene.py $P/rot-scene-$mode > $P/rot-scene-$mode.log 2>&1; echo "scene $mode exit $?"
  ROT_OFF=$off VIEW_TAPE=1 python3 $D/tools/opt20_scene.py $P/rot-views-$mode > $P/rot-views-$mode.log 2>&1; echo "views $mode exit $?"
done
unset SCENE_NOMMU
for k in scene views; do
  (cd $D/tools && PATCH=59748:6 python3 check_opt20_mask_scene.py $P/rot-$k-off $P/rot-$k-on $P/rot-$k-comparison.json > $P/rot-$k-comparison.log 2>&1); echo "$k compare exit $?"
done
export CLOCK_NORMALIZE=1 EXTRA_UAE='--uae_rtc=none' PATCH_KIND=rot END_FIELD=2002
CONTROL=1 python3 $D/tools/opt20_balanced_profile.py $P/rot-off > $P/rot-off.log 2>&1; echo "off exit $? $(tail -1 $P/rot-off.log)"
for k in 1 2 3 4 5 6 7 8; do
  TEST_SEED=$P/rot-off-seed MATCH_ENTRY=$P/rot-off python3 $D/tools/opt20_balanced_profile.py $P/rot-on-$k > $P/rot-on-$k.log 2>&1; r=$?
  echo "on-$k exit $r $(cat $P/rot-on-$k/entry-match.json 2>/dev/null) $(tail -1 $P/rot-on-$k.log)"
  [ $r = 0 ] && break
  grep -q "startup mismatch" $P/rot-on-$k.log || break
done
