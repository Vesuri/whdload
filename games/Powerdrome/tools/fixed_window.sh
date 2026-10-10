#!/usr/bin/env bash
# Calibrate, reboot and capture from a route-specific anchor.
# Default: title inset. Practice: WHD_ARGS=CUSTOM5=2 ANCHOR=0x14764 FIELDS=500.
set -euo pipefail
cd "$(dirname "$0")/.."
source amiga/env.sh
OUT=${1:?output directory required}
mkdir -p "$OUT" tmp/cache
OUT=$(cd "$OUT" && pwd)
INPUT=${2:-tmp/build/Powerdrome-verify.slave}
cp "$INPUT" "$OUT/slave.slave"
export SLAVE="$OUT/slave.slave"
export JOY0=none JOY1=none DETERMINISTIC=1 WARP=1
export WHD_ARGS="${WHD_ARGS:-CUSTOM5=1}"
export CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}"
export EXTRA_ARGS="${EXTRA_ARGS:---slow_memory=1536}"
FIELDS=${FIELDS:-100}
export FIELDS ANCHOR=${ANCHOR:-0x1067e}
export CPU=${CPU:-68000} AMIGA_MODEL=${AMIGA_MODEL:-A500}
python3 - "$OUT" <<'PYCONFIG'
import hashlib,json,os,shutil,sys
from pathlib import Path
out=Path(sys.argv[1])
keys=('AMIGA_MODEL','CPU','CHIP_KB','FAST_KB','EXTRA_ARGS','WHD_ARGS','ANCHOR','FIELDS','SWAP_ONLY','PROBE_OFFSETS')
config={key:os.environ.get(key) for key in keys}
for key, filename in (('emulator_sha256', shutil.which(os.environ.get('FSUAE', 'fs-uae'))), ('kickstart_sha256', os.environ.get('KICKSTART'))):
    if filename:
        config[key]=hashlib.sha256(Path(filename).read_bytes()).hexdigest()
config['slave_sha256']=hashlib.sha256((out/'slave.slave').read_bytes()).hexdigest()
(out/'configuration.json').write_text(json.dumps(config,indent=2)+'\n')
PYCONFIG

if [ "$FAST_KB" -gt 0 ]; then BASE=0x200000; SIZE=$((FAST_KB*1024))
else BASE=0xc00000; SIZE=1572864; fi
pd() { python3 tools/powerdrome.py "$@"; }
cleanup() {
  python3 - <<'PYCLEAN' >/dev/null 2>&1 || true
import subprocess
try: subprocess.run(['python3','tools/powerdrome.py','quit'],timeout=5)
except subprocess.TimeoutExpired: pass
PYCLEAN
}
trap cleanup EXIT
cleanup
KEY=$(python3 - <<'PYKEY'
import hashlib,os
from pathlib import Path
h=hashlib.sha256(Path(os.environ['SLAVE']).read_bytes())
h.update(repr([(k,os.environ.get(k)) for k in ('AMIGA_MODEL','CPU','CHIP_KB','FAST_KB','EXTRA_ARGS','KICKSTART','WHD_ARGS')]).encode())
print(h.hexdigest()[:20])
PYKEY
)
CACHE=tmp/cache/hunk-$KEY.txt
start() {
  : > "$OUT/serve.log"
  python3 tools/powerdrome.py serve > "$OUT/serve.log" 2>&1 &
  SERVER=$!
  for ((i=0;i<${SERVE_WAIT:-300};i++)); do
    rg -q 'serving on' "$OUT/serve.log" && return
    kill -0 "$SERVER" 2>/dev/null || { cat "$OUT/serve.log"; return 1; }
    sleep 1
  done
  echo 'Timed out waiting for capture anchor' >&2
  return 1
}
dumpmem() {
  pd gdb "dump binary memory tmp/window-chip.bin 0 $((CHIP_KB*1024))" > /dev/null
  pd gdb "dump binary memory tmp/window-other.bin $BASE $((BASE+SIZE))" > /dev/null
}
locate() {
  python3 - "$BASE" <<'PYLOC'
from pathlib import Path
import sys
sys.path.insert(0,'tools')
from powerdrome_report import regions
r=regions(Path('tmp/window-other.bin').read_bytes(),int(sys.argv[1],0),Path('tmp/window-chip.bin').read_bytes())
print(next((hex(lo) for lo,hi,n,o in r if n=='game'),''))
PYLOC
}
if [ ! -s "$CACHE" ]; then
  unset BOOT_BREAK
  start
  hunk=
  for ((j=0;j<60;j++)); do
    pd wait 0.5 > /dev/null
    pd stop > /dev/null
    dumpmem
    hunk=$(locate)
    [ -n "$hunk" ] && break
  done
  [ -n "$hunk" ] || { echo 'Game not found' >&2; exit 1; }
  printf '%s\n' "$hunk" > "$CACHE"
  cleanup
fi
hunk=$(cat "$CACHE")
# Optional ordered, read-only checkpoints before the measured anchor.
read -r -a PROBES <<< "${PROBE_OFFSETS:-}"
FIRST=${PROBES[0]:-$ANCHOR}
export BOOT_BREAK=$((hunk+FIRST))
start
for probe in "${PROBES[@]}"; do
  [ "$probe" = "$FIRST" ] || pd until "$((hunk+probe))" > "$OUT/probe-$probe-stop.txt"
  pd gdb 'info registers' > "$OUT/probe-$probe-registers.txt"
  python3 - "$OUT/probe-$probe-registers.txt" "$((hunk+probe))" <<'PYPROBE'
import re,sys
m=re.search(r'^pc\s+(0x[0-9a-f]+)',open(sys.argv[1]).read(),re.M)
assert m and int(m[1],16)==int(sys.argv[2]), 'Capture did not reach a requested probe'
PYPROBE
  dumpmem
  cp tmp/window-chip.bin "$OUT/probe-$probe-chip.bin"
  cp tmp/window-other.bin "$OUT/probe-$probe-other.bin"
done
if [ "${#PROBES[@]}" -gt 0 ]; then pd until "$((hunk+ANCHOR))" > "$OUT/anchor-stop.txt"; fi
dumpmem
[ "$(locate)" = "$hunk" ] || { echo 'Calibration mismatch' >&2; exit 1; }
pd gdb 'info registers pc sp' > "$OUT/anchor.txt"
python3 - "$OUT/anchor.txt" "$((hunk+ANCHOR))" <<'PYANCHOR'
import re,sys
s=open(sys.argv[1]).read()
m=re.search(r'^pc\s+(0x[0-9a-f]+)',s,re.M)
assert m and int(m[1],16)==int(sys.argv[2]), 'Capture did not reach the requested anchor'
PYANCHOR
cp tmp/window-chip.bin "$OUT/chip.bin"
cp tmp/window-other.bin "$OUT/code.bin"
printf '%s\n' "$hunk" > "$OUT/game-base.txt"
printf '%s\n' "$BASE" > "$OUT/dump-base.txt"
if [ "${SWAP_ONLY:-0}" = 1 ]; then
  MARKER=${SWAP_MARKER:-0x1067e}
  [[ "$WHD_ARGS" != *CUSTOM5=2* ]] || MARKER=${SWAP_MARKER:-0xbc7c}
  python3 tools/swap_fields.py "$FIELDS" "$OUT" "$OUT/code.bin" "$BASE" --marker "$MARKER"
else
pd profile "$FIELDS" "$OUT/trace.bin" > "$OUT/capture.txt"
python3 tools/powerdrome_report.py "$OUT/trace.bin" "$OUT/code.bin" --base "$BASE" > "$OUT/profile.txt"
if [[ "$WHD_ARGS" != *CUSTOM5=2* ]] && [ "$((ANCHOR))" -eq "$((0x1067e))" ]; then
  python3 tools/frames.py "$OUT/trace.bin" "$OUT/code.bin" "$BASE" > "$OUT/frames.txt"
fi
python3 - "$OUT" "$FIELDS" <<'PYSHOTS'
from pathlib import Path
import sys
sys.path.insert(0,'tools');import barto
p=Path(sys.argv[1]); t=barto.load(p/'trace.bin')
assert len(t.fields) == int(sys.argv[2]), 'Profiler returned fewer fields than requested'
(p/'first.png').write_bytes(t.fields[0].shot)
(p/'last.png').write_bytes(t.fields[-1].shot)
assert any(pc is not None for pc,c,r in t.instructions(t.fields[0])), 'No instruction PCs'
PYSHOTS
fi
dumpmem
cp tmp/window-chip.bin "$OUT/final-chip.bin"
cp tmp/window-other.bin "$OUT/final-code.bin"
if [ "${CAPTURE_SHOT:-0}" = 1 ]; then pd shot "$OUT/last.png" > "$OUT/shot.txt"; fi
cp amiga/.run/fsuae.log "$OUT/emulator.log"
cleanup
trap - EXIT
printf 'Captured %s fields in %s\n' "$FIELDS" "$OUT"
