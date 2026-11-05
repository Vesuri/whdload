#!/bin/zsh
set -e
. tmp/dev/amiga/env.sh
for arm in accepted production; do
 ARM="$arm" python3 tmp/dev/tools/capture_production_profile.py a1200-fast
 name="c4-q03-production-profile-$arm-a1200-fast-candidate"
 EXCLUDE_PACING=1 DROP_UPDATES=1 MAX_UPDATES=20 python3 tmp/dev/tools/analyze_step5_profile.py "$name" > "tmp/dev/tmp/step5/$name/analyze.log"
 EXCLUDE_PACING=1 DROP_UPDATES=1 MAX_UPDATES=20 python3 tmp/dev/tools/percar_step5_profile.py "$name" 0 0 > "tmp/dev/tmp/step5/$name/percar.log"
 EXCLUDE_PACING=1 DROP_UPDATES=1 MAX_UPDATES=20 python3 tmp/dev/tools/classify_step5_profile.py "$name" 0 0 > "tmp/dev/tmp/step5/$name/classify.log"
 python3 tmp/dev/tools/debt_step5_b8.py "$name"
 python3 tmp/dev/tools/audit_step5_b7_profile.py "$name"
 python3 tmp/dev/tools/archive_profile_traces.py "$name"
done
