#!/usr/bin/env bash
# Serial pixel/register/flag validation of the rendering patches in this revision.
#   tools/render_validate.sh PREFIX [CUSTOM2_BITS]
# Retain one exact VERIFY build; calibrate each CPU before arming startup aborts.
set -euo pipefail
cd "$(dirname "$0")/.."
. amiga/env.sh
PREFIX=${1:?capture prefix required}
[[ "$PREFIX" =~ ^[A-Za-z0-9_-]+$ ]] || { echo 'invalid capture prefix' >&2; exit 1; }
BITS=${2:-3}
if [ "$#" -lt 2 ]; then
  for feature in 'walls.s:7' 'sprites.s:15' 'rays.s:31' 'clear.s:63'; do
    name=${feature%:*}
    if rg -q "INCLUDE[[:space:]]+$name" whdload/LegendsOfValourHD.s; then BITS=${feature#*:}; fi
  done
fi
TWINS=$((BITS & 60))
OPTIONS=$((3 | (TWINS << 2)))
export UNTIL_TIMEOUT=${UNTIL_TIMEOUT:-300}
BUILD="tmp/prof/$PREFIX-build"
make -s -C whdload verify OUT="../$BUILD" VASMFLAGS="${VASMFLAGS:-} -DVERIFY_WAIT_RESCUE=1"
unset PROFILE_WINDOW BOOT_BREAK
for machine in a1200 a500; do
  base=0xc00000
  args=(AMIGA_MODEL=A500 CPU=68000 CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536)
  if [ "$machine" = a1200 ]; then
    base=0x200000
    args=(AMIGA_MODEL=A1200 "KICKSTART=$KICKSTART_A1200" CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 EXTRA_ARGS=--slow_memory=0)
  fi
  cal="tmp/prof/$PREFIX-cal-$machine"
  out="tmp/prof/$PREFIX-twin-$machine"
  for dest in "$cal" "$out"; do
    mkdir -p "$dest"
    cp "$BUILD/LegendsOfValour.Slave" "$dest/slave.slave"
    cp "$BUILD/LegendsOfValour.lst" "$dest/slave.lst"
  done
  env "${args[@]}" KEEP_SLAVE=1 STATE_ONLY=1 TAPE_OPTIONS=1 "WHD_ARGS=CUSTOM2=$BITS" \
    tools/fixed_window.sh "$cal" tools/tapes/c2p-views.txt > "$cal/capture.log" 2>&1
  boot=$(python3 - "$cal" "$base" <<'PY'
import os,re,sys
from pathlib import Path
sys.path.insert(0,'tools')
from lov_report import regions
p=Path(sys.argv[1]);base=int(sys.argv[2],0);os.environ['SLAVE']=str(p/'slave.slave')
slave=next(lo for lo,hi,n,o in regions((p/'code.bin').read_bytes(),base) if n=='slave')
m=re.search(r'^_patchgame\s+00:([0-9A-F]{8})\s*$',(p/'slave.lst').read_text(errors='replace'),re.M)
assert m, 'startup patch symbol absent'
print(hex(slave+int(m[1],16)))
PY
)
  env "${args[@]}" KEEP_SLAVE=1 "BOOT_BREAK=$boot" "TAPE_OPTIONS=$OPTIONS" \
    "WHD_ARGS=CUSTOM2=$BITS" SELFTEST_FRAMES="${SELFTEST_FRAMES:-300}" \
    tools/fixed_window.sh "$out" tools/tapes/c2p-views.txt > "$out/capture.log" 2>&1
  python3 tools/c2p_check.py "$out" --base "$base" --require-all-views
  python3 tools/render_check.py "$out" --base "$base" --bits "$TWINS" --all-variants > "$out/render-check.txt"
  cat "$out/render-check.txt"
done
