#!/bin/bash
# tools/matrix.sh [FILTER]: the render check and the play check on the a500, a1200,
# a1200-030 and a1200-040, and as the installed icon runs it (CUSTOM1=1 DCACHE, the -icon
# lines) on the last three, the check after a change (docs/development.md#the-matrix).
# FULL=1: every machine and WHDLoad cache option and the controls that must fail, for a
# question that needs them (an hour). Two runs at a time, started a few seconds apart.
# FILTER (a grep pattern) picks lines of the list below. Results go to tmp/matrix/: one log
# per line and summary.txt; the exit status is non-zero if any line did not give its
# expected result.
set -u
cd "$(dirname "$0")/.."
# name | check (render, play) | expected (pass, fail) | run options; * marks the minimal set
LIST='
*a500                |render|pass|SETUP=a500
*a500                |play  |pass|SETUP=a500
a500-ef              |render|pass|SETUP=a500 WHD_ARGS=CUSTOM1=1
*a1200               |render|pass|SETUP=a1200
*a1200               |play  |pass|SETUP=a1200
a1200-ef             |render|pass|SETUP=a1200 WHD_ARGS=CUSTOM1=1
*a1200-icon          |render|pass|SETUP=a1200 "WHD_ARGS=CUSTOM1=1 DCACHE"
*a1200-icon          |play  |pass|SETUP=a1200 "WHD_ARGS=CUSTOM1=1 DCACHE"
020-z3               |render|pass|SETUP=a1200 FAST_KB=0 "EXTRA_ARGS=--cpu=68020 --uae_cpu_frequency=28375160 --fast_memory=0 --zorro_iii_memory=32768"
020-z3               |play  |pass|SETUP=a1200 FAST_KB=0 "EXTRA_ARGS=--cpu=68020 --uae_cpu_frequency=28375160 --fast_memory=0 --zorro_iii_memory=32768"
020-z3-ef            |render|pass|SETUP=a1200 FAST_KB=0 WHD_ARGS=CUSTOM1=1 "EXTRA_ARGS=--cpu=68020 --uae_cpu_frequency=28375160 --fast_memory=0 --zorro_iii_memory=32768"
*030                 |render|pass|SETUP=a1200-030
*030                 |play  |pass|SETUP=a1200-030
030-ef               |render|pass|SETUP=a1200-030 WHD_ARGS=CUSTOM1=1
*030-icon            |render|pass|SETUP=a1200-030 "WHD_ARGS=CUSTOM1=1 DCACHE"
*030-icon            |play  |pass|SETUP=a1200-030 "WHD_ARGS=CUSTOM1=1 DCACHE"
030-mmu              |render|pass|SETUP=a1200-030 "WHD_ARGS=MMU"
030-mmu-nocache      |render|pass|SETUP=a1200-030 "WHD_ARGS=MMU NOCACHE"
030-mmu-cache        |render|pass|SETUP=a1200-030 "WHD_ARGS=MMU CACHE"
030-mmu-dcache       |render|pass|SETUP=a1200-030 "WHD_ARGS=MMU DCACHE"
030-mmu-dcache       |play  |pass|SETUP=a1200-030 "WHD_ARGS=MMU DCACHE"
*040                 |render|pass|SETUP=a1200-040
*040                 |play  |pass|SETUP=a1200-040
040-ef               |render|pass|SETUP=a1200-040 WHD_ARGS=CUSTOM1=1
040-ef               |play  |pass|SETUP=a1200-040 WHD_ARGS=CUSTOM1=1
*040-icon            |render|pass|SETUP=a1200-040 "WHD_ARGS=CUSTOM1=1 DCACHE"
*040-icon            |play  |pass|SETUP=a1200-040 "WHD_ARGS=CUSTOM1=1 DCACHE"
040-ef-nocache       |render|pass|SETUP=a1200-040 "WHD_ARGS=CUSTOM1=1 NOCACHE"
040-nocache          |render|pass|SETUP=a1200-040 WHD_ARGS=NOCACHE
040-cache            |render|pass|SETUP=a1200-040 WHD_ARGS=CACHE
040-dcache           |render|pass|SETUP=a1200-040 WHD_ARGS=DCACHE
040-dcache           |play  |pass|SETUP=a1200-040 WHD_ARGS=DCACHE
040-dcache-chipnc    |render|pass|SETUP=a1200-040 "WHD_ARGS=DCACHE CHIPNOCACHE"
060                  |render|pass|SETUP=a1200-060
060                  |play  |pass|SETUP=a1200-060
060-ef               |render|pass|SETUP=a1200-060 WHD_ARGS=CUSTOM1=1
060-ef               |play  |pass|SETUP=a1200-060 WHD_ARGS=CUSTOM1=1
060-icon             |render|pass|SETUP=a1200-060 "WHD_ARGS=CUSTOM1=1 DCACHE"
060-ef-movep-trap    |render|pass|SETUP=a1200-060 WHD_ARGS=CUSTOM1=1 "EXTRA_ARGS=--uae_cpu_no_unimplemented=true"
060-nocache          |render|pass|SETUP=a1200-060 WHD_ARGS=NOCACHE
060-cache            |render|pass|SETUP=a1200-060 WHD_ARGS=CACHE
060-dcache           |render|pass|SETUP=a1200-060 WHD_ARGS=DCACHE
060-dcache           |play  |pass|SETUP=a1200-060 WHD_ARGS=DCACHE
060-dcache-chipnc    |render|pass|SETUP=a1200-060 "WHD_ARGS=DCACHE CHIPNOCACHE"
060-branch-dcache    |render|pass|SETUP=a1200-060 "WHD_ARGS=BRANCHCACHE DCACHE"
060-movep-trap       |render|pass|SETUP=a1200-060 "EXTRA_ARGS=--uae_cpu_no_unimplemented=true"
control-v101-040     |render|fail|SETUP=a1200-040 SLAVE=original
control-v101-sound   |play  |fail|SETUP=a500 SLAVE=original
'
out=tmp/matrix; mkdir -p "$out"; : > "$out/summary.txt"
lines=$(printf '%s\n' "$LIST" | grep -v '^ *$')
[ "${FULL:-0}" = 1 ] || lines=$(printf '%s\n' "$lines" | grep '^\*')
lines=$(printf '%s\n' "$lines" | sed 's/^\*//' | grep -e "${1:-.}")
n=0 status=0 pids=''
run() {   # run INDEX NAME CHECK EXPECTED OPTIONS
  local i=$1 name=$2 check=$3 want=$4 opts=$5 got
  eval "set -- $opts"
  if tools/${check}_check.sh "$@" INSTANCE=m$i > "$out/$i-$name-$check.log" 2>&1; then got=pass; else got=fail; fi
  if [ $got = $want ]; then r=ok; else r=WRONG; fi
  printf '%-5s %-20s %-6s %s (expected %s): %s\n' $r "$name" $check $got $want \
    "$(grep -h 'check:' "$out/$i-$name-$check.log" | tail -1)" >> "$out/summary.txt"
}
while IFS='|' read -r name check want opts; do
  n=$((n + 1))
  name=$(echo $name) check=$(echo $check)
  run $n "$name" "$check" "$want" "$opts" &
  pids="$pids $!"
  if [ $((n % 2)) = 0 ]; then wait $pids; pids=''; else sleep 5; fi
done <<EOF
$lines
EOF
wait $pids
sort -k2 "$out/summary.txt" -o "$out/summary.txt"
cat "$out/summary.txt"
grep -q '^WRONG' "$out/summary.txt" && status=1
echo "matrix: $(grep -c '^ok' "$out/summary.txt") of $(wc -l < "$out/summary.txt" | tr -d ' ') as expected"
exit $status
