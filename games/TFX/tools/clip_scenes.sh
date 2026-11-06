#!/bin/bash
# Step 3b controlled scenes: SCAN_OFF control vs span clipping, cockpit (400) and views.
set -u
cd "$(dirname "$0")/.."
D=$PWD;P=$D/tmp/step3
export FSUAE=$D/tmp/opt20-project-emulator/fs-uae/fs-uae PROFILE_SLAVE=$P/${SLAVE_NAME:-clip}.slave DELTA_LISTING=$P/${SLAVE_NAME:-clip}.lst SCENE_NOMMU=1
T=${TAG:-clip}
for mode in off on; do
  off=; [ $mode = off ] && off=1
  SCAN_OFF=$off SCENE_SWAPS=400 python3 $D/tools/opt20_scene.py $P/$T-scene-$mode > $P/$T-scene-$mode.log 2>&1; echo "scene $mode exit $? $(cat $P/$T-scene-$mode/clip-stats.json 2>/dev/null | tr -d ' \n')"
  SCAN_OFF=$off VIEW_TAPE=1 python3 $D/tools/opt20_scene.py $P/$T-views-$mode > $P/$T-views-$mode.log 2>&1; echo "views $mode exit $? $(cat $P/$T-views-$mode/clip-stats.json 2>/dev/null | tr -d ' \n')"
done
cd $D/tools
for k in scene views; do
  PATCH=6c4f2:6 python3 check_opt20_mask_scene.py $P/$T-$k-off $P/$T-$k-on $P/$T-$k-comparison.json > $P/$T-$k-comparison.log 2>&1; echo "$k compare exit $?"
done
