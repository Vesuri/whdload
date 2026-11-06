#!/bin/bash
# Step 1 controlled scenes (cockpit, views) and balanced 2,000-field pair, CUSTOM1=0 vs 1.
set -u
cd "$(dirname "$0")/.."
D=$PWD;P=$D/tmp/prof20
export FSUAE=$D/tmp/opt20-project-emulator/fs-uae/fs-uae PROFILE_SLAVE=$P/intproj.slave DELTA_LISTING=$P/intproj.lst SCENE_NOMMU=1
if [ -z "${SKIP_SCENES:-}" ]; then
for c in 0 1; do
  CUSTOM1=$c python3 $D/tools/opt20_scene.py $P/intproj-scene-c1$c > $P/intproj-scene-c1$c.log 2>&1; echo "scene c1$c exit $?"
  CUSTOM1=$c VIEW_TAPE=1 python3 $D/tools/opt20_scene.py $P/intproj-views-c1$c > $P/intproj-views-c1$c.log 2>&1; echo "views c1$c exit $?"
done
(cd $D/tools && PATCH=55e32:6 python3 check_opt20_mask_scene.py $P/intproj-scene-c10 $P/intproj-scene-c11 $P/intproj-scene-comparison.json >/dev/null 2>&1; echo "scene compare exit $?"
 PATCH=55e32:6 python3 check_opt20_mask_scene.py $P/intproj-views-c10 $P/intproj-views-c11 $P/intproj-views-comparison.json >/dev/null 2>&1; echo "views compare exit $?")
fi
unset SCENE_NOMMU
# The seed bakes the WHDLoad arguments: both sides boot CUSTOM1=0 and the candidate
# selects project_int_040 by one same-address, same-length JMP write.
export PATCH_KIND=project END_FIELD=2002
[ -d $P/intproj-fpu ] || { python3 $D/tools/opt20_balanced_profile.py $P/intproj-fpu > $P/intproj-fpu.log 2>&1; echo "fpu exit $?"; }
for k in 1 2 3; do
  PROJECT_SYMBOL=project_int_040 TEST_SEED=$P/intproj-fpu-seed MATCH_ENTRY=$P/intproj-fpu python3 $D/tools/opt20_balanced_profile.py $P/intproj-int-$k > $P/intproj-int-$k.log 2>&1; r=$?
  echo "int-$k exit $r $(cat $P/intproj-int-$k/entry-match.json 2>/dev/null)"
  [ $r = 0 ] && break
  # Retry only a rejected start (startup mismatch), never a failed measurement.
  grep -q "startup mismatch" $P/intproj-int-$k.log || break
done
