#!/bin/bash
# Step 6 (32-byte compare lines): native copy twins, CPU/option gates, controlled scenes
# against the production loop, and the clock-normalized balanced 2,000-field pair.
set -u
cd "$(dirname "$0")/.."
D=$PWD;P=$D/tmp/copy6
export FSUAE=$D/tmp/opt20-project-emulator/fs-uae/fs-uae PROFILE_SLAVE=$P/copy.slave DELTA_LISTING=$P/copy.lst COPY_DONOR=$D/tmp/prof20/intproj-verified COPY_LEN=150
if [ -z "${LATE_ONLY:-}" ]; then
rm -rf $P/copy-tests $P/copy-tests-seed
python3 $D/tools/opt20_delta_test.py $P/copy-tests > $P/copy-tests.log 2>&1 && (cd $D/tools && python3 check_opt20_delta.py $P/copy-tests) >> $P/copy-tests.log 2>&1
r=$?; echo "twins exit $r $(tail -2 $P/copy-tests.log | tr '\n' ' ' | cut -c1-300)"; [ $r = 0 ] || exit 1
for g in "040 0" "040 0 original" "060 0" "030 0" "040 1"; do
  set -- $g; n=copy-gate-$1-c5$2${3:+-$3}
  CUSTOM5=$2 python3 $D/tools/opt20_gate.py $P/$n $1 ${3:-} > $P/$n.log 2>&1; echo "$n exit $?"
done
fi
export SCENE_NOMMU=1 COPY_BENCH=1
for mode in off on; do
  off=; [ $mode = off ] && off=1
  WORD_COPY_OFF=$off SCENE_SWAPS=400 python3 $D/tools/opt20_scene.py $P/copy-scene-$mode > $P/copy-scene-$mode.log 2>&1; echo "scene $mode exit $?"
  WORD_COPY_OFF=$off VIEW_TAPE=1 python3 $D/tools/opt20_scene.py $P/copy-views-$mode > $P/copy-views-$mode.log 2>&1; echo "views $mode exit $?"
done
unset SCENE_NOMMU COPY_BENCH
for k in scene views; do
  (cd $D/tools && PATCH=0:0 python3 check_opt20_mask_scene.py $P/copy-$k-off $P/copy-$k-on $P/copy-$k-comparison.json > $P/copy-$k-comparison.log 2>&1); echo "$k compare exit $?"
done
export CLOCK_NORMALIZE=1 EXTRA_UAE='--uae_rtc=none' PATCH_KIND=copy END_FIELD=2002
CONTROL=1 python3 $D/tools/opt20_balanced_profile.py $P/copy-off > $P/copy-off.log 2>&1; echo "off exit $? $(tail -1 $P/copy-off.log)"
for k in 1 2 3 4 5 6 7 8; do
  TEST_SEED=$P/copy-off-seed MATCH_ENTRY=$P/copy-off python3 $D/tools/opt20_balanced_profile.py $P/copy-on-$k > $P/copy-on-$k.log 2>&1; r=$?
  echo "on-$k exit $r $(cat $P/copy-on-$k/entry-match.json 2>/dev/null) $(tail -1 $P/copy-on-$k.log)"
  [ $r = 0 ] && break
  grep -q "startup mismatch" $P/copy-on-$k.log || break
done
