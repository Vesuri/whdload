#!/bin/bash
# Step 4 (scanline span setup): native twins, CPU/option gates, controlled scenes
# with the original routine, and the clock-normalized balanced 2,000-field pair.
set -u
cd "$(dirname "$0")/.."
D=$PWD;P=$D/tmp/sfd4
export DEBUG_PORT=${DEBUG_PORT:-2611} FSUAE=$D/tmp/opt20-project-emulator/fs-uae/fs-uae PROFILE_SLAVE=$P/sfd.slave DELTA_LISTING=$P/sfd.lst
if [ -z "${LATE_ONLY:-}" ]; then
rm -rf $P/sfd-tests $P/sfd-tests-seed
(cd $D/tools && python3 opt20_sfd_test.py $P/sfd-tests) > $P/sfd-tests.log 2>&1
r=$?; echo "twins exit $r $(tail -2 $P/sfd-tests.log | tr '\n' ' ' | cut -c1-300)"; [ $r = 0 ] || exit 1
for g in "040 0" "040 0 original" "060 0" "030 0" "040 1"; do
  set -- $g; n=sfd-gate-$1-c5$2${3:+-$3}
  CUSTOM5=$2 python3 $D/tools/opt20_gate.py $P/$n $1 ${3:-} > $P/$n.log 2>&1; echo "$n exit $?"
done
fi
export SCENE_NOMMU=1
for mode in off on; do
  off=; [ $mode = off ] && off=1
  SFD_OFF=$off SCENE_SWAPS=400 python3 $D/tools/opt20_scene.py $P/sfd-scene-$mode > $P/sfd-scene-$mode.log 2>&1; echo "scene $mode exit $?"
  SFD_OFF=$off VIEW_TAPE=1 python3 $D/tools/opt20_scene.py $P/sfd-views-$mode > $P/sfd-views-$mode.log 2>&1; echo "views $mode exit $?"
done
# Scratch registers D1-D6/A1/A6 at exit poisoned with fixed junk: the scenes must not change.
PROFILE_SLAVE=$P/sfd-poison.slave DELTA_LISTING=$P/sfd-poison.lst SCENE_SWAPS=400 python3 $D/tools/opt20_scene.py $P/sfd-scene-poison > $P/sfd-scene-poison.log 2>&1; echo "scene poison exit $?"
PROFILE_SLAVE=$P/sfd-poison.slave DELTA_LISTING=$P/sfd-poison.lst VIEW_TAPE=1 python3 $D/tools/opt20_scene.py $P/sfd-views-poison > $P/sfd-views-poison.log 2>&1; echo "views poison exit $?"
unset SCENE_NOMMU
for k in scene views; do
  (cd $D/tools && PATCH=6c514:6 python3 check_opt20_mask_scene.py $P/sfd-$k-on $P/sfd-$k-poison $P/sfd-$k-poison-comparison.json > $P/sfd-$k-poison-comparison.log 2>&1); echo "$k poison compare exit $?"
done
for k in scene views; do
  (cd $D/tools && PATCH=6c514:6 python3 check_opt20_mask_scene.py $P/sfd-$k-off $P/sfd-$k-on $P/sfd-$k-comparison.json > $P/sfd-$k-comparison.log 2>&1); echo "$k compare exit $?"
done
export CLOCK_NORMALIZE=1 EXTRA_UAE='--uae_rtc=none' PATCH_KIND=sfd END_FIELD=2002
CONTROL=1 python3 $D/tools/opt20_balanced_profile.py $P/sfd-off > $P/sfd-off.log 2>&1; echo "off exit $? $(tail -1 $P/sfd-off.log)"
for k in 1 2 3 4 5 6 7 8; do
  TEST_SEED=$P/sfd-off-seed MATCH_ENTRY=$P/sfd-off python3 $D/tools/opt20_balanced_profile.py $P/sfd-on-$k > $P/sfd-on-$k.log 2>&1; r=$?
  echo "on-$k exit $r $(cat $P/sfd-on-$k/entry-match.json 2>/dev/null) $(tail -1 $P/sfd-on-$k.log)"
  [ $r = 0 ] && break
  grep -q "startup mismatch" $P/sfd-on-$k.log || break
done
