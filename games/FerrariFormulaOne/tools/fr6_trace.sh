#!/bin/bash
# fr6_trace.sh TAG: trace tmp/build/fr6-TAG (tools/fr6_build.py TAG) on 030-50-bce as a
# 68EC030 for 60 fields with capture_hi25_profile.py, then print the cost per routine
# (fr6_owners.py). Absolute trace milliseconds read about 1.5-1.9x high; use the shares.
set -eu
cd "$(dirname "$0")/.."
. ../../common/env.sh >/dev/null 2>&1
v=${1:?usage: fr6_trace.sh TAG}
b="$PWD/tmp/build/fr6-$v"
tag="fr6-prof-$v"
mkdir -p tmp/logs
if ! env H5_BUILD="$b" FF1_BUILD="$b" C1_VARIANT="$tag" \
  RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache' \
  RELEASE_PROFILE_OVERRIDES='{"CPU":"68EC030"}' HI25_FIELDS=60 \
  python3 tools/capture_hi25_profile.py 030-50-bce > "tmp/logs/$tag.log" 2>&1; then
  echo "capture failed: tmp/logs/$tag.log"
  exit 1
fi
python3 tools/fr6_owners.py "tmp/step5/hi25-profile-030-50-bce-$tag" | head -40
