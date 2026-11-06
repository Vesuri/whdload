#!/bin/bash
# Step 7 (palette blend, factor 50 as a copy): native twins, CPU/option gates, controlled scenes
# with the original routine, and the clock-normalized balanced 2,000-field pair.
set -u
cd "$(dirname "$0")/.."
D=$PWD;P=$D/tmp/fade7
export FSUAE=$D/tmp/opt20-project-emulator/fs-uae/fs-uae PROFILE_SLAVE=$P/fade.slave DELTA_LISTING=$P/fade.lst
if [ -z "${LATE_ONLY:-}" ]; then
rm -rf $P/fade-tests $P/fade-tests-seed
(cd $D/tools && python3 opt20_fade_test.py $P/fade-tests) > $P/fade-tests.log 2>&1
r=$?; echo "twins exit $r $(tail -2 $P/fade-tests.log | tr '\n' ' ' | cut -c1-300)"; [ $r = 0 ] || exit 1
for g in "040 0" "040 0 original" "060 0" "030 0" "040 1"; do
  set -- $g; n=fade-gate-$1-c5$2${3:+-$3}
  CUSTOM5=$2 python3 $D/tools/opt20_gate.py $P/$n $1 ${3:-} > $P/$n.log 2>&1; echo "$n exit $?"
done
fi
export SCENE_NOMMU=1
for mode in off on; do
  off=; [ $mode = off ] && off=1
  FADE_OFF=$off SCENE_SWAPS=400 python3 $D/tools/opt20_scene.py $P/fade-scene-$mode > $P/fade-scene-$mode.log 2>&1; echo "scene $mode exit $?"
  FADE_OFF=$off VIEW_TAPE=1 python3 $D/tools/opt20_scene.py $P/fade-views-$mode > $P/fade-views-$mode.log 2>&1; echo "views $mode exit $?"
done
unset SCENE_NOMMU
for k in scene views; do
  (cd $D/tools && PATCH=249a:6 python3 check_opt20_mask_scene.py $P/fade-$k-off $P/fade-$k-on $P/fade-$k-comparison.json > $P/fade-$k-comparison.log 2>&1); echo "$k compare exit $?"
done
export CLOCK_NORMALIZE=1 EXTRA_UAE='--uae_rtc=none' PATCH_KIND=fade END_FIELD=2002
CONTROL=1 python3 $D/tools/opt20_balanced_profile.py $P/fade-off > $P/fade-off.log 2>&1; echo "off exit $? $(tail -1 $P/fade-off.log)"
for k in 1 2 3 4 5 6 7 8; do
  TEST_SEED=$P/fade-off-seed MATCH_ENTRY=$P/fade-off python3 $D/tools/opt20_balanced_profile.py $P/fade-on-$k > $P/fade-on-$k.log 2>&1; r=$?
  echo "on-$k exit $r $(cat $P/fade-on-$k/entry-match.json 2>/dev/null) $(tail -1 $P/fade-on-$k.log)"
  [ $r = 0 ] && break
  grep -q "startup mismatch" $P/fade-on-$k.log || break
done
