#!/bin/bash
# Step 3b balanced pair, started only when the shared host is quiet enough for
# repeatable boots (under load the boot's stop point drifts; see clip-off-nepeat).
set -u
cd "$(dirname "$0")/.."
D=$PWD;P=$D/tmp/step3
for i in $(seq 1 240); do
  load=$(sysctl -n vm.loadavg | awk '{print $2}')
  awk -v l="$load" -v m="${MAX_LOAD:-12}" 'BEGIN{exit !(l<m)}' && break
  sleep 60
done
echo "start load $(sysctl -n vm.loadavg)"
# The OS boot jitters run to run (boot snapshots always differ slightly); the game's
# startup state then matches only sometimes. MATCH_ENTRY stays exact; the start is
# retried up to 8 times (decided before the timing window, so no selection bias),
# with the emulated RTC disabled and the vblank clock normalized on both sides.
export CLOCK_NORMALIZE=1 EXTRA_UAE='--uae_rtc=none' FSUAE=$D/tmp/opt20-project-emulator/fs-uae/fs-uae PROFILE_SLAVE=$P/clip.slave DELTA_LISTING=$P/clip.lst PATCH_KIND=scan END_FIELD=2002
CONTROL=1 python3 $D/tools/opt20_balanced_profile.py $P/clip-off-n > $P/clip-off-n.log 2>&1; echo "off exit $?"
for k in 1 2 3 4 5 6 7 8; do
  TEST_SEED=$P/clip-off-n-seed MATCH_ENTRY=$P/clip-off-n python3 $D/tools/opt20_balanced_profile.py $P/clip-on-n$k > $P/clip-on-n$k.log 2>&1; r=$?
  echo "on-n$k exit $r $(cat $P/clip-on-n$k/entry-match.json 2>/dev/null) load $(sysctl -n vm.loadavg)"
  [ $r = 0 ] && break
  grep -q "startup mismatch" $P/clip-on-n$k.log || break
done
