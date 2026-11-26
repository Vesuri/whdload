#!/bin/bash
# The original's baseline (resolution plan step 1): both views, two scenes, one machine.
#
#   tools/baseline.sh MODE MACHINE OUT
#     MODE     frames: frame counts on the normal FS-UAE and the machine's own setup;
#              aprof: per-field cycle profiles on $FSUAE_APROF (no MMU: the cycle-exact CPU
#              on the a1200-fast base, as aprof requires)
#     MACHINE  a1200-fast (the 68020 reference: the plain a1200's 2 MB cannot hold the
#              slave's 1.4 MB ExpMem), a1200-030 or a1200-040
#     OUT      directory for the results (under tmp/)
#
# Two boots, each deterministic (WARP=1 DETERMINISTIC=1 JOY0=none) into level 1 with mouse
# control: the first measures standing at the start in the small view, then in full screen,
# then the scripted walk (ab3d.py SCRIPTS) in the small view; the second the walk in full
# screen. Each measurement is FIELDS fields (default 500; the walk is 550).
set -eu
mode=$1 machine=$2 out=$3
game=$(cd "$(dirname "$0")/.." && pwd)
cd "$game"
. ../../common/env.sh
mkdir -p "$out"
out=$(cd "$out" && pwd)
fields=${FIELDS:-500}
export INSTANCE=baseline-$mode-$machine WARP=1 WINDOW=none DETERMINISTIC=1 JOY0=none
case $mode in
  frames) export SETUP=$machine ;;
  aprof)
    export FSUAE=$FSUAE_APROF
    case $machine in
      a1200-fast) export SETUP=a1200-fast ;;
      a1200-030) export SETUP=a1200-fast
        EXTRA_ARGS='--cpu=68EC030 --uae_cpu_frequency=50000000 --uae_cpu_data_cache=true' ;;
      a1200-040) export SETUP=a1200-fast
        EXTRA_ARGS='--cpu=68040-NOMMU --uae_cpu_frequency=25000000 --uae_cpu_data_cache=true' ;;
      *) echo "unknown machine $machine" >&2; exit 2 ;;
    esac
    export EXTRA_ARGS=${EXTRA_ARGS:-} ;;
  *) echo "unknown mode $mode" >&2; exit 2 ;;
esac

ab3d() { python3 tools/ab3d.py "$@"; }

measure() {   # NAME FIELDS [SCRIPT]
  local name=$1 n=$2
  shift 2
  if [ "$mode" = aprof ]; then
    ab3d aprof "$n" "$out/$name.json" "$@" | tee -a "$out/log.txt"
    python3 tools/frametime.py "$out/$name.json" > "$out/$name.txt"
  else
    { printf '%s: ' "$name"; ab3d frames "$n" "$@"; } | tee -a "$out/$name.txt" "$out/log.txt"
  fi
  ab3d shot "$out/$name.png" > /dev/null
}

boot() {
  python3 tools/ab3d.py serve > "$out/serve.log" 2>&1 &
  local i=0
  until [ -S "tmp/run/$INSTANCE/.run/ab3d.sock" ] && grep -q '^serving' "$out/serve.log"; do
    i=$((i + 1))
    [ $i -lt 120 ] || { echo 'server did not start' >&2; cat "$out/serve.log" >&2; exit 1; }
    sleep 0.5
  done
  ab3d wait 20 > /dev/null
  ab3d level | tee -a "$out/log.txt"
  ab3d base > "$out/base.txt"
}

trap 'ab3d quit > /dev/null 2>&1 || true' EXIT
echo "$mode $machine: SETUP=$SETUP FSUAE=${FSUAE:-default} EXTRA_ARGS=${EXTRA_ARGS:-}" | tee "$out/log.txt"
boot
measure start-small "$fields"
ab3d full 1 | tee -a "$out/log.txt"
measure start-full "$fields"
ab3d full 0 | tee -a "$out/log.txt"
measure walk-small 550 walk
ab3d quit > /dev/null
sleep 1
boot
ab3d full 1 | tee -a "$out/log.txt"
measure walk-full 550 walk
