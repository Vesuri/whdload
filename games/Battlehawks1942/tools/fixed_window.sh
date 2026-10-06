#!/usr/bin/env bash
# Benchmark window: trace FIELDS PAL fields of the first training flight from its first frame.
# tools/fixed_window.sh OUTDIR [SLAVE]
# There is no attract demo. The VERIFY slave's input tape (whdload/tape.s) answers the manual
# check, picks Select Training and accepts the defaults, so the flight starts by itself.
# The anchor is the first execution of bh:1a2c2, the 3D view's chunky-to-planar pass, after
# the tape's last key; menus and screens never run it, so it is the flight's first frame.
# SKIP_FRAMES=N starts the window N frames later. ANCHOR overrides the hunk offset.
# SWAP_ONLY=1 counts frames with breakpoints instead of tracing (68030: no instruction trace).
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=$1; mkdir -p "$OUT"; FIELDS=${FIELDS:-100}
export CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" EXTRA_ARGS="${EXTRA_ARGS---slow_memory=1536}"
# The host mouse feeds port 0 even with input grab off (seen in the input recordings); the
# game only needs the tape's keys, so captures run with nothing in the joystick ports.
export JOY0="${JOY0:-none}" JOY1="${JOY1:-none}"
# Retain exactly the slave used by this capture; later builds must not change region sizes
# or hook addresses when analysing a saved trace. The default is a fresh VERIFY build (tape).
INPUT_SLAVE=${2:-}
if [ -z "$INPUT_SLAVE" ]; then
  make -s -C whdload verify > /dev/null
  INPUT_SLAVE=whdload/Battlehawks1942.Slave
fi
if [ "$INPUT_SLAVE" != "$PWD/$OUT/slave.slave" ]; then
  cp "$INPUT_SLAVE" "$OUT/slave.slave"
fi
export DETERMINISTIC=1 SLAVE="$PWD/$OUT/slave.slave" CPU="${CPU:-68000}"
# The Kickstart and the slave live in "other" memory: fast RAM at $200000 when there is any,
# else slow RAM. BH itself is always in chip RAM (the slave's 512 KB BaseMem).
SLOW_KB=$(sed -n 's/.*--slow_memory=\([0-9]*\).*/\1/p' <<< "$EXTRA_ARGS")
if [ "$FAST_KB" -gt 0 ]; then BASE=0x200000; SIZE=$((FAST_KB * 1024))
else BASE=0xc00000; SIZE=$((${SLOW_KB:-512} * 1024)); fi
CHIP_END=$(printf '%#x' $((CHIP_KB * 1024)))
bh() { python3 tools/bh.py "$@"; }
[ -S amiga/.run/bh.sock ] && { bh quit > /dev/null 2>&1 || true; sleep 1; }
rm -f amiga/.run/serve.log "$OUT/trace.bin"
WARP=1 python3 tools/bh.py serve > amiga/.run/serve.log 2>&1 &
trap 'bh quit > /dev/null 2>&1 || true' EXIT
SERVER=$!
for _ in $(seq 1 120); do
  grep -q serving amiga/.run/serve.log 2>/dev/null && break
  kill -0 "$SERVER" 2>/dev/null || { cat amiga/.run/serve.log >&2; exit 1; }
  sleep 1
done
grep -q serving amiga/.run/serve.log || { echo "server did not start" >&2; exit 1; }

# gdb splits arguments at spaces, so dump through space-free paths. Retry: the dump
# occasionally fails to appear (seen on A1200 configurations in Indianapolis 500).
dump() {
  local reply
  for _ in $(seq 1 12); do
    reply=$(bh gdb "dump binary memory /tmp/bh-code.bin $BASE $(printf '%#x' $((BASE + SIZE)))
dump binary memory /tmp/bh-chip.bin 0 $CHIP_END")
    if [ -f /tmp/bh-code.bin ] && [ -f /tmp/bh-chip.bin ]; then
      mv /tmp/bh-code.bin "$OUT/code.bin"; mv /tmp/bh-chip.bin "$OUT/chip.bin"; return 0
    fi
    echo "memory not ready, retrying: ${reply: -300}" >&2
    kill -0 "$(cat amiga/.run/fsuae.pid)" 2>/dev/null || return 1
    bh wait 1 > /dev/null
  done
  return 1
}
# Prints "BH-hunk tape-counter-address tape-end", or nothing before BH is loaded.
locate() {
  python3 -c "
import struct, sys; sys.path.insert(0, 'tools'); from bh_report import regions
code, chip = open('$OUT/code.bin', 'rb').read(), open('$OUT/chip.bin', 'rb').read()
r = {n: lo for lo, hi, n, o in regions(code, $BASE, chip)}
i = code.find(b'BHTAPE!!')
if 'bh' in r and i >= 0:
    print(hex(r['bh']), hex($BASE + i + 8), struct.unpack_from('>I', code, i + 12)[0])"
}
# No breakpoint during the boot: warp with a breakpoint armed is far too slow for the ~4500
# fields before the flight. The tape publishes its field count; poll it (read-only, emulated
# time stands still while gdb holds the CPU) and arm the anchor ARM_EARLY fields before the
# tape's last key, so the first c2p pass cannot be missed.
loc=
for _ in $(seq 1 120); do
  bh wait 1 > /dev/null
  dump
  loc=$(locate)
  [ -n "$loc" ] && break
done
[ -n "$loc" ] || { echo "BH (or the VERIFY tape) never appeared in memory" >&2; exit 1; }
read -r hunk counter tape_end <<< "$loc"
echo "BH code hunk at $hunk; tape counter at $counter, last key at field $tape_end"
arm=$((tape_end - ${ARM_EARLY:-300}))
while :; do
  n=$(bh gdb "x/1wx $counter" | awk '/:/ {print $2}')
  [ $((n)) -ge "$arm" ] && break
  bh wait 0.2 > /dev/null
done
anchor=$(printf '%#x' $((hunk + ${ANCHOR:-0x1a2c2})))
bh until "$anchor" > "$OUT/anchor.txt"
dump
[ "$(locate | cut -d' ' -f1)" = "$hunk" ] || { echo "BH moved" >&2; exit 1; }
bh gdb 'info registers pc sp' >> "$OUT/anchor.txt"
if [ "${SKIP_FRAMES:-0}" -gt 0 ]; then
  bh gdb "break *$(printf '%#x' $((hunk + ${ANCHOR:-0x1a2c2})))
ignore \$bpnum $((SKIP_FRAMES - 1))
continue
delete" >> "$OUT/anchor.txt"
fi
retain_log() { cp amiga/.run/fsuae.log "$OUT/fsuae.log"; }
if [ "${SWAP_ONLY:-0}" = 1 ]; then
  python3 tools/swap_fields.py "$FIELDS" "$OUT" "$OUT/code.bin" "$BASE" "$OUT/chip.bin"
  bh quit > /dev/null; trap - EXIT
  retain_log
  exit 0
fi
reply=$(bh profile "$FIELDS" "$PWD/$OUT/trace.bin")
[ -f "$OUT/trace.bin" ] || { echo "no trace: $reply" >&2; exit 1; }
dump
bh quit > /dev/null; trap - EXIT
retain_log
python3 - "$OUT" <<'EOF'
import sys; sys.path.insert(0, 'tools'); import barto
out = sys.argv[1]; t = barto.load(f'{out}/trace.bin')
open(f'{out}/first.png', 'wb').write(t.fields[0].shot)
open(f'{out}/last.png', 'wb').write(t.fields[-1].shot)
EOF
python3 tools/frames.py "$OUT/trace.bin" "$OUT/code.bin" "$BASE" | tee "$OUT/frames.txt"
