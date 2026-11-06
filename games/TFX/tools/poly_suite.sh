#!/bin/bash
# Step 5 (fused edge walking): native twins, CPU/option gates, controlled scenes
# with the original routine, and the clock-normalized balanced 2,000-field pair.
set -u
cd "$(dirname "$0")/.."
D=$PWD;P=$D/tmp/poly5
export DEBUG_PORT=${DEBUG_PORT:-2611} FSUAE=$D/tmp/opt20-project-emulator/fs-uae/fs-uae PROFILE_SLAVE=$P/poly.slave DELTA_LISTING=$P/poly.lst
if [ -z "${LATE_ONLY:-}" ]; then
rm -rf $P/poly-tests $P/poly-tests-seed
(cd $D/tools && python3 opt20_poly_test.py $P/poly-tests) > $P/poly-tests.log 2>&1
r=$?; echo "twins exit $r $(tail -2 $P/poly-tests.log | tr '\n' ' ' | cut -c1-300)"; [ $r = 0 ] || exit 1
for g in "040 0" "040 0 original" "060 0" "030 0" "040 1"; do
  set -- $g; n=poly-gate-$1-c5$2${3:+-$3}
  CUSTOM5=$2 python3 $D/tools/opt20_gate.py $P/$n $1 ${3:-} > $P/$n.log 2>&1; echo "$n exit $?"
done
fi
export SCENE_NOMMU=1
for mode in off on; do
  off=; [ $mode = off ] && off=1
  POLY_OFF=$off SCENE_SWAPS=400 python3 $D/tools/opt20_scene.py $P/poly-scene-$mode > $P/poly-scene-$mode.log 2>&1; echo "scene $mode exit $?"
  POLY_OFF=$off VIEW_TAPE=1 python3 $D/tools/opt20_scene.py $P/poly-views-$mode > $P/poly-views-$mode.log 2>&1; echo "views $mode exit $?"
done
# Exit registers, flags and the unwritten scratch memory poisoned with fixed junk: the scenes must not change.
PROFILE_SLAVE=$P/poly-poison.slave DELTA_LISTING=$P/poly-poison.lst SCENE_SWAPS=400 python3 $D/tools/opt20_scene.py $P/poly-scene-poison > $P/poly-scene-poison.log 2>&1; echo "scene poison exit $?"
PROFILE_SLAVE=$P/poly-poison.slave DELTA_LISTING=$P/poly-poison.lst VIEW_TAPE=1 python3 $D/tools/opt20_scene.py $P/poly-views-poison > $P/poly-views-poison.log 2>&1; echo "views poison exit $?"
unset SCENE_NOMMU
for k in scene views; do
  (cd $D/tools && PATCH=60d92:6 python3 check_opt20_mask_scene.py $P/poly-$k-on $P/poly-$k-poison $P/poly-$k-poison-comparison.json > $P/poly-$k-poison-comparison.log 2>&1); echo "$k poison compare exit $?"
done
for k in scene views; do
  (cd $D/tools && PATCH=60d92:6 python3 check_opt20_mask_scene.py $P/poly-$k-off $P/poly-$k-on $P/poly-$k-comparison.json > $P/poly-$k-comparison.log 2>&1); echo "$k compare exit $?"
done
export CLOCK_NORMALIZE=1 EXTRA_UAE='--uae_rtc=none' PATCH_KIND=poly END_FIELD=2002
CONTROL=1 python3 $D/tools/opt20_balanced_profile.py $P/poly-off > $P/poly-off.log 2>&1; echo "off exit $? $(tail -1 $P/poly-off.log)"
for k in 1 2 3 4 5 6 7 8; do
  TEST_SEED=$P/poly-off-seed MATCH_ENTRY=$P/poly-off python3 $D/tools/opt20_balanced_profile.py $P/poly-on-$k > $P/poly-on-$k.log 2>&1; r=$?
  echo "on-$k exit $r $(cat $P/poly-on-$k/entry-match.json 2>/dev/null) $(tail -1 $P/poly-on-$k.log)"
  [ $r = 0 ] && break
  grep -q "startup mismatch" $P/poly-on-$k.log || break
done
