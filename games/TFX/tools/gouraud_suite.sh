#!/bin/bash
# Gouraud runs (gouraud_runs): native twins, CPU/option gates, controlled scenes
# (action, views, follow camera) against gouraud_fill_new, and clock-normalized balanced
# 2,000-field pairs on the action and follow-camera tapes.
set -u
cd "$(dirname "$0")/.."
D=$PWD;P=${GF_DIR:-$D/tmp/gouraud}
export DEBUG_PORT=${DEBUG_PORT:-2611} FSUAE=$D/tmp/opt20-project-emulator/fs-uae/fs-uae PROFILE_SLAVE=$P/gf.slave DELTA_LISTING=$P/gf.lst
python3 $D/tools/check_gf_table.py $DELTA_LISTING || exit 1
if [ -z "${LATE_ONLY:-}" ]; then
if [ -z "${SKIP_TWINS:-}" ]; then
rm -rf $P/gf-tests $P/gf-tests-seed
(cd $D/tools && python3 opt20_gouraud_test.py $P/gf-tests ${PROBE_JSON:-$P/probe/gouraud.json}) > $P/gf-tests.log 2>&1
r=$?; echo "twins exit $r $(tail -2 $P/gf-tests.log | tr '\n' ' ' | cut -c1-300)"; [ $r = 0 ] || exit 1
fi
for g in "040 0" "040 0 original" "060 0" "030 0" "040 1"; do
  set -- $g; n=gf-gate-$1-c5$2${3:+-$3}
  CUSTOM5=$2 python3 $D/tools/opt20_gate.py $P/$n $1 ${3:-} > $P/$n.log 2>&1; echo "$n exit $?"
done
fi
if [ -z "${PAIRS_ONLY:-}" ]; then
export SCENE_NOMMU=1
for mode in off on; do
  off=; [ $mode = off ] && off=1
  GOURAUD_OFF=$off SCENE_SWAPS=400 python3 $D/tools/opt20_scene.py $P/gf-scene-$mode > $P/gf-scene-$mode.log 2>&1; echo "scene $mode exit $?"
  GOURAUD_OFF=$off VIEW_TAPE=1 python3 $D/tools/opt20_scene.py $P/gf-views-$mode > $P/gf-views-$mode.log 2>&1; echo "views $mode exit $?"
  GOURAUD_OFF=$off FOLLOW_TAPE=1 SCENE_SWAPS=400 python3 $D/tools/opt20_scene.py $P/gf-follow-$mode > $P/gf-follow-$mode.log 2>&1; echo "follow $mode exit $?"
done
unset SCENE_NOMMU
for k in scene views follow; do
  (cd $D/tools && PATCH=4f840:6 python3 check_opt20_mask_scene.py $P/gf-$k-off $P/gf-$k-on $P/gf-$k-comparison.json > $P/gf-$k-comparison.log 2>&1); echo "$k compare exit $?"
done
fi
export CLOCK_NORMALIZE=1 EXTRA_UAE='--uae_rtc=none' PATCH_KIND=gouraud END_FIELD=2002
for tape in ${TAPES:-follow action}; do
  [ $tape = follow ] && export FLIGHT_TAPE=$D/tools/follow.tape.json || unset FLIGHT_TAPE
  CONTROL=1 python3 $D/tools/opt20_balanced_profile.py $P/gf-pair-$tape-off > $P/gf-pair-$tape-off.log 2>&1; echo "$tape off exit $? $(tail -1 $P/gf-pair-$tape-off.log)"
  for k in 1 2 3 4 5 6 7 8; do
    TEST_SEED=$P/gf-pair-$tape-off-seed MATCH_ENTRY=$P/gf-pair-$tape-off python3 $D/tools/opt20_balanced_profile.py $P/gf-pair-$tape-on-$k > $P/gf-pair-$tape-on-$k.log 2>&1; r=$?
    echo "$tape on-$k exit $r $(cat $P/gf-pair-$tape-on-$k/entry-match.json 2>/dev/null) $(tail -1 $P/gf-pair-$tape-on-$k.log)"
    [ $r = 0 ] && break
    grep -q "startup mismatch" $P/gf-pair-$tape-on-$k.log || break
  done
done
