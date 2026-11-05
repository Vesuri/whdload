#!/bin/bash
# Ramp and handling plans for su17 and b13 on the faster profiles, from the game directory.
. tools/env.sh >/dev/null 2>&1
L="h3-ramp-50 h3-ramp-60 h3-ramp-70 h3-ramp-80 h3-ramp-90 h3-ramp-100 h3-ramp-110 c1c-60 c1e-lim-brake c1f-90-brake h3-hill-spin"
python3 tools/build_feel.py --prefix su17- $L > /dev/null 2>&1 || echo "su17 build failed"
python3 tools/build_feel.py --source "$PWD/tmp/base13f/src" --prefix b13- $L > /dev/null 2>&1 || echo "b13 build failed"
cd tools || exit 1
for prof in a1200-020 a4000-060-50; do
  t=$(echo "$prof" | tr -cd 'a-z0-9' | tail -c 4)
  python3 run_feel.py su17-$t --profile $prof --custom1 2 --jobs 4 --prefix su17- --tag s$t $L 2>&1 | tail -n 11
  python3 run_feel.py b13-$t --profile $prof --custom1 2 --jobs 4 --prefix b13- --tag b$t $L 2>&1 | tail -n 11
done
