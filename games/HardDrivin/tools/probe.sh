#!/bin/bash
# Build and run C4 probes (SCENARIO, default loop_follow; SUMMARY, default loop_pass.py): tools/probe.sh PROFILE FIELDS NAME:ENV... (from the game directory)
# NAME:ENV is e.g. ls2-559:C4_STEER=1,C4_VELOCITY=559. Prints loop_pass for each.
. tools/env.sh >/dev/null 2>&1
profile=$1; fields=$2; shift 2
names=""
for spec in "$@"; do
  name=${spec%%:*}; envs=${spec#*:}
  if ! env $(echo "$envs" | tr ',' ' ') python3 tools/build_c4_geometry_probe.py "$name" ${SCENARIO:-loop_follow} > "tmp/build/$name.build.log" 2>&1; then
    grep -i error "tmp/build/$name.build.log" | head -3; continue
  fi
  names="$names $name"
done
cd tools || exit 1
tag=$(echo "$profile" | tr -cd 'a-z0-9' | tail -c 4)
for name in $names; do
  run="$name-$tag"; n=1
  while [ -e "../tmp/prof/$run" ]; do n=$((n + 1)); run="$name-$tag-$n"; done
  INSTANCE="p$name$tag" python3 capture_c4_input.py "$run" --profile "$profile" --slave "$name.slave" --custom1 2 --fields "$fields" --terrain --native-pose > "../tmp/prof/$run.out" 2>&1 &
  echo "$run" >> ../tmp/probe.runs.$$
done
wait
cd .. || exit 1
for run in $(cat tmp/probe.runs.$$ 2>/dev/null); do python3 -I tools/${SUMMARY:-loop_pass.py} "$run" 2>&1 | tail -1; done
mv tmp/probe.runs.$$ tmp/probe.last 2>/dev/null
