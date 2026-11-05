#!/bin/bash
# Step C manoeuvre matrix: c_runs.sh ROOT [SHIFT] runs every manoeuvre into
# ROOT/NAME (8 MAME sessions at a time). SHIFT (seconds, default 0) delays the
# manoeuvres for the repeat runs. Analyse with tools/feel.py report ROOT.
set -u
root=$1
shift_s=${2:-0}
here=$(cd "$(dirname "$0")" && pwd)
p="$here/plans"
mkdir -p "$root"
# name|plan|emulated seconds|environment
runs="
c1a-auto|c1a_auto|130|
c1a-stick|c1a_stick|130|
c1b-full|c1b_brake|96|
c1b-half|c1b_brake|96|HD_BRAKE=1500
c1c-30|c1c_ramp|70|HD_MPH=30 HD_LOCK=0.5
c1c-60|c1c_ramp|75|HD_MPH=60 HD_LOCK=0.3
c1c-90|c1c_ramp|80|HD_MPH=90 HD_LOCK=0.2
c1d-30|c1d_step|60|HD_MPH=30 HD_SMALL=250 HD_LARGE=650
c1d-60|c1d_step|65|HD_MPH=60 HD_SMALL=105 HD_LARGE=260
c1d-90|c1d_step|70|HD_MPH=90 HD_SMALL=80 HD_LARGE=235
c1e-mid-lift|c1e_corner|60|HD_MPH=60 HD_WHEEL=180 HD_ACTION=lift
c1e-mid-brake|c1e_corner|60|HD_MPH=60 HD_WHEEL=180 HD_ACTION=brake
c1e-mid-power|c1e_corner|60|HD_MPH=60 HD_WHEEL=180 HD_ACTION=power
c1e-lim-lift|c1e_corner|60|HD_MPH=60 HD_WHEEL=240 HD_ACTION=lift
c1e-lim-brake|c1e_corner|60|HD_MPH=60 HD_WHEEL=240 HD_ACTION=brake
c1e-lim-power|c1e_corner|60|HD_MPH=60 HD_WHEEL=240 HD_ACTION=power
c1f-60-counter|c1f_slide|60|HD_MPH=60 HD_WHEEL=650 HD_ACTION=counter
c1f-60-hold|c1f_slide|60|HD_MPH=60 HD_WHEEL=650 HD_ACTION=hold
c1f-60-release|c1f_slide|60|HD_MPH=60 HD_WHEEL=650 HD_ACTION=release
c1f-90-counter|c1f_slide|65|HD_MPH=90 HD_WHEEL=600 HD_ACTION=counter
c1f-90-hold|c1f_slide|65|HD_MPH=90 HD_WHEEL=600 HD_ACTION=hold
c1f-90-release|c1f_slide|65|HD_MPH=90 HD_WHEEL=600 HD_ACTION=release
c1f-60-brake|c1f_slide|60|HD_MPH=60 HD_WHEEL=260 HD_ACTION=release HD_BRAKE=1
c1f-90-brake|c1f_slide|65|HD_MPH=90 HD_WHEEL=235 HD_ACTION=release HD_BRAKE=1
c1g|c1g_lock|124|
"
n=0
IFS='
'
for line in $runs; do
  IFS='|' read -r name plan secs envs <<< "$line"
  (
    IFS=' '
    for kv in $envs; do export "$kv"; done
    HD_SHIFT=$shift_s HD_SECONDS=$((secs + 3)) HD_WALL=150 "$here/session.sh" "$root/$name" "$p/$plan.lua" >/dev/null 2>&1
    echo "$name: $(tail -1 "$root/$name/mame.out" 2>/dev/null)"
  ) &
  n=$((n + 1))
  if [ $n -ge 8 ]; then wait; n=0; fi
done
wait
