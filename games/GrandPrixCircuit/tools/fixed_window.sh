#!/usr/bin/env bash
# Fixed GPC window: first race-loop entry, then SKIP_FIELDS VBLs (default 300).
# tools/fixed_window.sh OUTDIR [SLAVE]
# Build with make verify; VERIFY supplies the RNG and joystick instruments.
# Use WHD_ARGS="CUSTOM2=0 CUSTOM3=1 CUSTOM5=1". ANCHOR overrides the race offset.
set -euo pipefail
cd "$(dirname "$0")/.."
. ../../common/env.sh
OUT=$1; mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"; FIELDS=${FIELDS:-100}
export FIELDS SKIP_FIELDS="${SKIP_FIELDS:-300}"
export CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" SLOW_KB="${SLOW_KB:-1536}"
# Retain exactly the slave used by this capture; later builds must not change
# region sizes or hook addresses when analysing a saved trace.
INPUT_SLAVE=${2:-${SLAVE:-tmp/build/verify/GrandPrixCircuit.Slave}}
if [ "$INPUT_SLAVE" != "$OUT/slave.slave" ]; then
  cp "$INPUT_SLAVE" "$OUT/slave.slave"
  if [ -f "${INPUT_SLAVE%.*}.lst" ]; then cp "${INPUT_SLAVE%.*}.lst" "$OUT/slave.slave.lst"; fi
fi
python3 -c 'import sys; assert b"GPCVERIFY\0" in open(sys.argv[1],"rb").read(), "fixed_window requires a VERIFY slave"' "$OUT/slave.slave"
export JOY0="${JOY0:-none}" JOY1="${JOY1:-none}"
export DETERMINISTIC=1 SLAVE="$OUT/slave.slave" CPU="${CPU:-68000}"
# The code is loaded into "other" memory: fast RAM at $200000 when there is any, else slow RAM.
SLOW_KB="${SLOW_KB:-1536}"
if [ "$FAST_KB" -gt 0 ]; then BASE=0x200000; SIZE=$((FAST_KB * 1024))
else BASE=0xc00000; SIZE=$((${SLOW_KB:-512} * 1024)); fi
# Cache only the address, keyed by machine, arguments and slave build. A calibration
# boot discovers it; the measurement boot arms the race breakpoint at CPU reset.
mkdir -p tmp/prof
KEY=$(python3 -c 'import hashlib,os; from pathlib import Path; p=os.environ.get("SLAVE") or "tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/GrandPrixCircuit.Slave"; h=hashlib.sha256(Path(p).read_bytes()); h.update(repr([(k,os.environ.get(k)) for k in ("AMIGA_MODEL","KICKSTART","CPU","CHIP_KB","FAST_KB","SLOW_KB","EXTRA_ARGS","WHD_ARGS")]).encode()); print(h.hexdigest()[:20])')
CACHE="tmp/prof/hunk-$KEY.txt"
BOOT_HUNK=${BOOT_HUNK:-$(cat "$CACHE" 2>/dev/null || true)}
if [ -n "$BOOT_HUNK" ]; then export BOOT_BREAK=$(printf '%#x' $((BOOT_HUNK + ${ANCHOR:-0x7094}))); fi
gpc() { python3 tools/gpc.py "$@"; }
retain_log() {
  cp tmp/run/default/.run/fsuae.log "$OUT/fsuae-stdout.log"
  local logfile
  logfile=$(sed -n 's/^LOGFILE: //p' tmp/run/default/.run/fsuae.log | tail -1)
  if [ -n "$logfile" ] && [ -f "$logfile" ]; then
    cp "$logfile" "$OUT/fsuae.log"
  else
    cp tmp/run/default/.run/fsuae.log "$OUT/fsuae.log"
  fi
}
[ -S tmp/run/default/.run/gpc.sock ] && { gpc quit > /dev/null 2>&1 || true; sleep 1; }
rm -f tmp/run/default/.run/serve.log "$OUT/trace.bin"
WARP=1 python3 tools/gpc.py serve > tmp/run/default/.run/serve.log 2>&1 &
trap 'gpc quit > /dev/null 2>&1 || true' EXIT
SERVER=$!
for _ in $(seq 1 "${SERVE_WAIT:-180}"); do
  grep -q serving tmp/run/default/.run/serve.log 2>/dev/null && break
  kill -0 "$SERVER" 2>/dev/null || { cat tmp/run/default/.run/serve.log >&2; exit 1; }
  sleep 1
done
grep -q serving tmp/run/default/.run/serve.log || { echo "race breakpoint not reached" >&2; exit 1; }

gpc gdb 'set remote memory-read-packet-size 1024' > "$OUT/dump-gdb.txt"
dump() {
  local reply
  reply=$(gpc gdb "dump binary memory tmp/run/default/.run/capture-code.bin $BASE $(printf '%#x' $((BASE + SIZE)))")
  printf '%s\n' "$reply" >> "$OUT/dump-gdb.txt"
  if [[ "$reply" == *"Invalid hex digit"* || "$reply" == *"Error"* || "$reply" == *"Cannot access"* ]]; then
    printf '%s\n' "$reply" >&2
    return 1
  fi
  mv tmp/run/default/.run/capture-code.bin "$OUT/code.bin"
}
hunk=
for _ in $(seq 1 60); do
  [ -n "$BOOT_HUNK" ] || gpc wait 1 > /dev/null
  dump
  hunk=$(python3 -c "
import struct
from pathlib import Path
d=Path('$OUT/code.bin').read_bytes(); hits=[]; i=-1
while (i:=d.find(b'GPCVERIFY\\0',i+1))>=0:
 h,v=struct.unpack_from('>II',d,i+10)
 if v==1 and $BASE<=h<$BASE+len(d) and d[h-$BASE:h-$BASE+2]==bytes.fromhex('6000'):hits.append(h)
assert len(hits)<=1, 'ambiguous live VERIFY record'
print(hex(hits[0]) if hits else '')")
  [ -n "$hunk" ] && break
done
[ -n "$hunk" ] || { echo "gpc never appeared in memory" >&2; exit 1; }
echo "gpc code hunk at $hunk"
if [ -z "$BOOT_HUNK" ]; then
  printf '%s\n' "$hunk" > "$CACHE"
  gpc quit > /dev/null; trap - EXIT
  echo "calibrated code address; rebooting with the race breakpoint armed"
  exec bash "$PWD/tools/fixed_window.sh" "$OUT" "$SLAVE"
fi
[ "$((hunk))" = "$((BOOT_HUNK))" ] || { echo "loaded hunk differs from boot breakpoint" >&2; exit 1; }
# Validated first race-loop anchor, armed from reset after calibration.
# Align to a native VBL boundary after a fixed 300-field warm-up from race entry.
SKIP_FIELDS=${SKIP_FIELDS:-300}
gpc gdb "break *$(printf '%#x' $((hunk + 0x772a)))" > "$OUT/anchor.txt"
gpc gdb "ignore \$bpnum $SKIP_FIELDS" >> "$OUT/anchor.txt"
gpc gdb continue >> "$OUT/anchor.txt"
gpc gdb delete >> "$OUT/anchor.txt"
gpc gdb 'info registers a4 pc' >> "$OUT/anchor.txt"
dump
cp "$OUT/code.bin" "$OUT/before.bin"
python3 tools/capture_metadata.py "$OUT" "$BASE"
if [[ "${WHD_ARGS:-}" == *CUSTOM1=1* ]]; then
  python3 - "$OUT" <<'PYGRID'
import json,struct,sys
from pathlib import Path
r=Path(sys.argv[1]);m=json.loads((r/'metadata.json').read_text());d=(r/'before.bin').read_bytes();a4=m['data_base']+0x7ffe-m['base']
assert struct.unpack_from('>h',d,a4+3846)[0]==1
order=struct.unpack_from('>10h',d,a4+3732)
assert sorted(order)==list(range(10)),('invalid grid',order)
slots=struct.unpack_from('>10I',d,a4+6)
assert all(slots) and len(set(slots))>=9,('uninitialised cars',slots)
print('Verified ten distinct car IDs and populated position slots:',order)
PYGRID
fi
if [ "${STATIONARY_AUDIT:-0}" = 1 ]; then
  python3 tools/stationary_draws.py "$OUT"
  gpc shot "$OUT/stationary.png" > "$OUT/shot.txt"
  dump
  gpc quit > /dev/null; trap - EXIT
  retain_log
  exit 0
fi
if [ "${PHASE3_FIELDS:-0}" -gt 0 ]; then
  if [ "${LAP_ONLY:-0}" = 1 ]; then
    python3 tools/phase6_lap_fields.py "$PHASE3_FIELDS" "$OUT"
  else
    python3 tools/phase3_fields.py "$PHASE3_FIELDS" "$OUT"
  fi
  dump
  gpc quit > /dev/null; trap - EXIT
  retain_log
  exit 0
fi
if [ "${INPUT_AUDIT:-0}" = 1 ]; then
  python3 tools/check_tape.py "$OUT"
  dump
  gpc quit > /dev/null; trap - EXIT
  retain_log
  exit 0
fi
# Optional read-only state study: sample N VBL entries before the traced window.
# The trace then starts after these N fields; record that offset when quoting its fps.
if [ "${STATE_FIELDS:-0}" -gt 0 ]; then
  python3 tools/state_fields.py "$STATE_FIELDS" "$OUT/state" "$OUT/code.bin" "$BASE"
fi
# State-only studies need no cycle trace or debugger attach to the host process.
# Deliberately emit no frame-rate figure in this mode.
if [ "${STATE_ONLY:-0}" = 1 ]; then
  [ "${STATE_FIELDS:-0}" -gt 0 ] || { echo "STATE_ONLY requires STATE_FIELDS" >&2; exit 1; }
  dump
  gpc quit > /dev/null; trap - EXIT
  retain_log
  echo "state-only capture complete (no frame-rate measurement)"
  exit 0
fi
if [ "${SWAP_ONLY:-0}" = 1 ]; then
  python3 tools/swap_fields.py "$FIELDS" "$OUT" "$OUT/code.bin" "$BASE"
  dump
  gpc quit > /dev/null; trap - EXIT
  retain_log
  exit 0
fi
reply=$(gpc profile "$FIELDS" "$OUT/trace.bin")
[ -f "$OUT/trace.bin" ] || { echo "no trace: $reply" >&2; exit 1; }
dump
gpc quit > /dev/null; trap - EXIT
retain_log
python3 - "$OUT" <<'EOF'
import sys; sys.path.insert(0, 'tools'); import _amigaxdev; from amigaxdev import barto
out = sys.argv[1]; t = barto.load(f'{out}/trace.bin')
open(f'{out}/first.png', 'wb').write(t.fields[0].shot)
open(f'{out}/last.png', 'wb').write(t.fields[-1].shot)
EOF
python3 tools/frames.py "$OUT/trace.bin" "$OUT/code.bin" "$BASE" | tee "$OUT/frames.txt"
