#!/usr/bin/env bash
# Flight record: boot the VERIFY slave, let the tape fly the first training flight, and save
# the flight record (src/tape.s: per flight frame the field count, T and the player's state)
# once it is full or covers RECORD_FIELDS fields.  tools/speed.py reads it.  Default slave:
# the rectime build (the flight tape in fields, the same input in real time on any machine).
#   tools/record.sh OUTDIR [SLAVE]
# MACHINE: a500 (68000, 512 KB chip + 8 MB fast, the capture machine; default), a1200
# (68020, 2 MB chip + 8 MB fast) or 030 (a1200-030: 68030/50, 8 MB fast).
# WHD_ARGS='CUSTOM2=1' flies with the Enhanced framerate.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=$1; mkdir -p "$OUT"
INPUT_SLAVE=${2:-}
if [ -z "$INPUT_SLAVE" ]; then
  make -s build BUILD=rectime > /dev/null
  INPUT_SLAVE=tmp/build/rectime/Battlehawks1942.Slave
fi
cp "$INPUT_SLAVE" "$OUT/slave.slave"
case "${MACHINE:-a500}" in
  a500) export SETUP=custom CPU=68000 CHIP_KB=512 FAST_KB=8192 ;;
  a1200) export SETUP=custom AMIGA_MODEL=A1200 KICKSTART="$KICKSTART_A1200" CPU=68020 \
           CHIP_KB=2048 FAST_KB=8192 ;;
  030) export SETUP=a1200-030 ;;
  *) echo "MACHINE: a500, a1200 or 030" >&2; exit 2 ;;
esac
export DETERMINISTIC=1 SLAVE="$PWD/$OUT/slave.slave" JOY0=none JOY1=none
echo "${MACHINE:-a500} ${WHD_ARGS:-}" > "$OUT/machine.txt"
BASE=0x200000; SIZE=$((8192 * 1024)); CHIP_END=$((2048 * 1024))
RUN="tmp/run/${INSTANCE:-default}/.run"
mkdir -p "$RUN"
bh() { python3 tools/bh.py "$@"; }
[ -S "$RUN"/bh.sock ] && { bh quit > /dev/null 2>&1 || true; sleep 1; }
rm -f "$RUN"/serve.log
WARP=1 WINDOW=none python3 tools/bh.py serve > "$RUN"/serve.log 2>&1 &
trap 'bh quit > /dev/null 2>&1 || true' EXIT
SERVER=$!
for _ in $(seq 1 120); do
  grep -q serving "$RUN"/serve.log 2>/dev/null && break
  kill -0 "$SERVER" 2>/dev/null || { cat "$RUN"/serve.log >&2; exit 1; }
  sleep 1
done
grep -q serving "$RUN"/serve.log || { echo "server did not start" >&2; exit 1; }

# The record's header in the running slave: "BHREC!!!", count, buffer, frames.
locate() {
  bh gdb "dump binary memory tmp/rec-code-${INSTANCE:-default}.bin $BASE $(printf '%#x' $((BASE + SIZE)))
dump binary memory tmp/rec-chip-${INSTANCE:-default}.bin 0 $(printf '%#x' $CHIP_END)" > /dev/null
  [ -f tmp/rec-code-${INSTANCE:-default}.bin ] && [ -f tmp/rec-chip-${INSTANCE:-default}.bin ] || return 0
  python3 -c "
import struct, sys; sys.path.insert(0, 'tools'); from bh_report import regions
code, chip = open('tmp/rec-code-${INSTANCE:-default}.bin', 'rb').read(), open('tmp/rec-chip-${INSTANCE:-default}.bin', 'rb').read()
r = {n: lo for lo, hi, n, o in regions(code, $BASE, chip)}
i = code.find(b'BHREC!!!', r['slave'] - $BASE) if 'slave' in r else -1
if 'bh' in r and i >= 0:
    print(hex($BASE + i + 8), struct.unpack_from('>I', code, i + 16)[0])"
  rm -f tmp/rec-code-${INSTANCE:-default}.bin tmp/rec-chip-${INSTANCE:-default}.bin
}
loc=
for _ in $(seq 1 120); do
  bh wait 2 > /dev/null
  bh stop > /dev/null
  loc=$(locate)
  bh cont > /dev/null
  [ -n "$loc" ] && break
done
[ -n "$loc" ] || { echo "BH (or the flight record) never appeared in memory" >&2; exit 1; }
read -r header frames <<< "$loc"
echo "flight record at $header, $frames frames"
# Until the record is full or covers RECORD_FIELDS fields (default 2000: 40 s of flight).
words() { bh gdb "x/3wx $header" | awk '/:/ {print $2, $3, $4}'; }
field() { bh gdb "x/1hx $1" | awk '/:/ {print $2}'; }
count=0
for _ in $(seq 1 1800); do
  read -r count buf _ <<< "$(words)"
  [ $((count)) -ge "$frames" ] && break
  if [ $((count)) -gt 1 ]; then
    first=$(field "$buf"); last=$(field "$(printf '%#x' $((buf + (count - 1) * 28)))")
    [ $(((last - first) & 0xffff)) -ge "${RECORD_FIELDS:-2000}" ] && break
  fi
  bh wait 1 > /dev/null
done
[ $((count)) -gt 1 ] || { echo "the flight never started (record empty)" >&2; exit 1; }
bh stop > /dev/null
read -r count buf _ <<< "$(words)"
[ $((count)) -le "$frames" ] || count=$frames
bh gdb "dump binary memory tmp/rec-${INSTANCE:-default}.bin $buf $(printf '%#x' $((buf + count * 28)))" > /dev/null
mv tmp/rec-${INSTANCE:-default}.bin "$OUT/record.bin"
bh shot "$PWD/$OUT/last.png" > /dev/null || true
bh quit > /dev/null; trap - EXIT
cp "$RUN"/fsuae.log "$OUT/fsuae.log" 2>/dev/null || true
python3 tools/speed.py "$OUT"
