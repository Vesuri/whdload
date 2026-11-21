#!/usr/bin/env bash
# Which per-pass routines of the main loop change the world state ($6577c, $18be1 bytes,
# what a save game holds)? Boots BUILD with WHD_ARGS on a500-020, stops at the loop's top
# at tick TICK (default 5) and dumps the state at each call site for PASSES passes
# (default 3). Sites in a pass without a tick ($12940) wait for the next tick's pass.
#   pass_writes.sh BUILD "WHD_ARGS" [TICK] [PASSES]
set -uo pipefail
cd "$(dirname "$0")/.."
. ../../common/env.sh 2>/dev/null
build="$1" args="$2" tick="${3:-5}" passes="${4:-3}"
srv() { python3 ../../common/tools/game_server.py "$@" 2>/dev/null; }
(make serve BUILD="$build" NOBUILD=1 SETUP=a500-020 WARP=1 WINDOW=none WB=0 WHD_ARGS="$args" > tmp/serve.log 2>&1 &)
for _ in $(seq 1 60); do srv wait 1 >/dev/null && break; sleep 1; done
srv stop >/dev/null
srv gdb "break *0x128ea if *(int*)0x535ba == $tick" >/dev/null
srv gdb continue >/dev/null
srv gdb delete >/dev/null
rm -rf tmp/pw; mkdir -p tmp/pw
n=0
for pass in $(seq "$passes"); do
  for site in 128ea 12940 1296a 129a2 129a8 129ae 129bc 129c2 129da 129e0 12a08 12a0e 12a14 13170 13184; do
    srv until "0x$site" >/dev/null
    n=$((n + 1)); printf -v f '%03d-%s' "$n" "$site"
    srv gdb dump binary memory "$PWD/tmp/pw/$f.bin" 0x6577c 0x7e35d >/dev/null
  done
done
srv gdb x/1wx 0x535ba | grep '^0x5'
srv quit >/dev/null
make -s stop >/dev/null 2>&1 || true   # the emulator of this game, pid-scoped
"$AMIGA_SHARE/python/bin/python3" -I - <<'PY'
import numpy as np
import glob, os
names = {'128ea':'top..12940','12940':'world step','1296a':'..129a2 (gates)','129a2':'waitswap','129a8':'12636 render','129ae':'pause test','129bc':'171d0+f152','129c2':'tick logic','129da':'7274','129e0':'8298+scroll','12a08':'da7c','12a0e':'7a38','12a14':'input..13170','13170':'swap','13184':'end'}
fs = sorted(glob.glob('tmp/pw/*.bin'))
d = [np.fromfile(f, np.uint8) for f in fs]
for i in range(len(fs) - 1):
    site = os.path.basename(fs[i])[4:-4]
    x = np.nonzero(d[i] != d[i+1])[0] + 0x6577c
    ppl = int(((x >= 0x77b7a)).sum())
    if len(x): print(f'{os.path.basename(fs[i])[:3]} {names.get(site, site):16} {len(x):6d} bytes, people {ppl:5d}', [hex(v) for v in x[:8]])
PY
