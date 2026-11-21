#!/usr/bin/env bash
# Check the partial copy of CUSTOM4 (copy only changed screen parts) for writes into the chip buffers that its
# shadows miss: boot the quick build (or BUILD=spin) with WHD_ARGS on SETUP, stop SAMPLES
# times at the main loop's top, and compare each chip buffer with its shadow where the
# shadow is valid.
#   shadowcheck.sh SETUP "WHD_ARGS" [SAMPLES] [EXTRA_ARGS]
set -uo pipefail
cd "$(dirname "$0")/.."
. ../../common/env.sh 2>/dev/null
setup="$1" args="$2" samples="${3:-20}" extra="${4:-}"
srv() { python3 ../../common/tools/game_server.py "$@" 2>/dev/null; }
rdl() { srv gdb x/1wx "$1" | awk '/^0x[0-9a-f]*:/ {print $2}'; }
(make serve BUILD="${BUILD:-quick}" NOBUILD=1 SETUP="$setup" WARP=1 WINDOW=none WB=0 WHD_ARGS="$args" EXTRA_ARGS="$extra" > tmp/serve.log 2>&1 &)
for _ in $(seq 1 60); do srv wait 1 >/dev/null && break; sleep 1; done
srv wait 30 >/dev/null
mkdir -p tmp/sc; rm -f tmp/sc/*
for i in $(seq "$samples"); do
  srv wait 2 >/dev/null
  srv until 0x128ea >/dev/null
  p=$(rdl 0xf4)
  s0=$(rdl "$p"); s1=$(rdl "$((p + 4))")
  srv gdb x/2xb "$((p + 8))" | awk '/^0x/ {print $2, $3}' > "tmp/sc/$i.ok"
  srv gdb dump binary memory "$PWD/tmp/sc/$i.c0" 0x434a6 $((0x434a6 + 32000)) >/dev/null
  srv gdb dump binary memory "$PWD/tmp/sc/$i.c1" 0x3b7a6 $((0x3b7a6 + 32000)) >/dev/null
  srv gdb dump binary memory "$PWD/tmp/sc/$i.s0" "$s0" $((s0 + 32000)) >/dev/null
  srv gdb dump binary memory "$PWD/tmp/sc/$i.s1" "$s1" $((s1 + 32000)) >/dev/null
  srv gdb x/1wx 0x535ba | awk '/^0x/ {print $2}' > "tmp/sc/$i.tick"
done
srv quit >/dev/null
make -s stop >/dev/null 2>&1 || true   # the emulator of this game, pid-scoped
"$AMIGA_SHARE/python/bin/python3" -I - "$samples" <<'PY'
import sys
bad = 0
for i in range(1, int(sys.argv[1]) + 1):
    ok = open(f'tmp/sc/{i}.ok').read().split()
    tick = open(f'tmp/sc/{i}.tick').read().strip()
    line = [f'sample {i:2} tick {tick}']
    for k in (0, 1):
        c = open(f'tmp/sc/{i}.c{k}', 'rb').read(); s = open(f'tmp/sc/{i}.s{k}', 'rb').read()
        d = sum(1 for a, b in zip(c, s) if a != b)
        valid = ok[k] != '0x00'
        line.append(f'buf{k} valid={int(valid)} diff={d}')
        if valid and d: bad += 1
    print('  '.join(line))
print('MISMATCHES WHERE VALID:', bad)
PY
