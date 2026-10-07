#!/usr/bin/env bash
# Benchmark window: trace FIELDS PAL fields of the first training flight, in a left turn.
# tools/fixed_window.sh OUTDIR [SLAVE]
# There is no attract demo. The VERIFY slave's input tape (whdload/tape.s) answers the manual
# check, picks Select Training and accepts the defaults, so the flight starts by itself.
# The anchor is bh:1a2c2, the 3D view's chunky-to-planar pass (menus and screens never run
# it), at flight frame SKIP_FRAMES by BH's own frame counter (default 90, inside the left turn
# the tape flies on the A500; its presses end about 335 fields after the last Return).
# ANCHOR overrides the hunk offset.
# SWAP_ONLY=1 counts frames with breakpoints instead of tracing (68030: no instruction trace).
# STATE_ONLY=1 only dumps memory at the c2p entry of flight frame SKIP_FRAMES.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=$1; mkdir -p "$OUT"; FIELDS=${FIELDS:-100}
# A500 with 8 MB of fast RAM: room for the slave's fast memory (BH) and for PRELOAD of all
# three disk images (without it every disk read is a WHDLoad OS switch, and boots blink).
export CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-8192}" EXTRA_ARGS="${EXTRA_ARGS:-}"
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
# The Kickstart, the slave and the slave's fast memory (BH's code, data and chunky buffers)
# live in "other" memory: fast RAM at $200000 when there is any, else slow RAM.
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
# Prints "BH-hunk tape-counter-address tape-end frame-counter-address", or nothing before BH
# is loaded. BH's frame counter is the word at 26292(a4) (a4 = data hunk + $7FFE), counted
# up once per pass of the flight loop (bh:6e52).
locate() {
  python3 -c "
import struct, sys; sys.path.insert(0, 'tools'); from bh_report import regions
code, chip = open('$OUT/code.bin', 'rb').read(), open('$OUT/chip.bin', 'rb').read()
r = {n: lo for lo, hi, n, o in regions(code, $BASE, chip)}
# The running slave's counter, not the one in WHDLoad's copy of the slave file.
i = code.find(b'BHTAPE!!', r['slave'] - $BASE) if 'slave' in r else -1
if 'bh' in r and i >= 0:
    print(hex(r['bh']), hex($BASE + i + 8), struct.unpack_from('>I', code, i + 12)[0],
          hex(r['bh-data'] + 0x7ffe + 26292))"
}
# No breakpoint during the boot: warp with a breakpoint armed is far too slow for the ~4500
# fields before the flight. The tape publishes its field count; poll it (read-only, emulated
# time stands still while gdb holds the CPU) and arm the anchor ARM_EARLY fields before the
# tape's last key, so the first c2p pass cannot be missed.
loc=
# Hold the emulator while dumping and searching (8 MB, seconds of Python): left running in
# warp it got thousands of fields past the arming point before the counter was found.
for _ in $(seq 1 120); do
  bh wait 1 > /dev/null
  bh stop > /dev/null
  dump
  loc=$(locate)
  [ -n "$loc" ] && break
done
[ -n "$loc" ] || { echo "BH (or the VERIFY tape) never appeared in memory" >&2; exit 1; }
read -r hunk counter tape_end frames <<< "$loc"
echo "BH code hunk at $hunk; tape counter at $counter, last key at field $tape_end"
# Warp runs hundreds of fields in a 0.2 s poll step: arm well before the flight can start.
arm=$((tape_end - ${ARM_EARLY:-1000}))
while :; do
  n=$(bh gdb "x/1wx $counter" | awk '/:/ {print $2}')
  [ $((n)) -ge "$arm" ] && break
  bh wait 0.05 > /dev/null
done
echo "armed at tape field $((n))" > "$OUT/armed.txt"
anchor=$(printf '%#x' $((hunk + ${ANCHOR:-0x1a2c2})))
bh until "$anchor" > "$OUT/anchor.txt"
dump
[ "$(locate | cut -d' ' -f1)" = "$hunk" ] || { echo "BH moved" >&2; exit 1; }
bh gdb 'info registers pc sp' >> "$OUT/anchor.txt"
# The window opens at the c2p pass of flight frame SKIP_FRAMES (BH's frame counter), not N
# passes after the first one seen: on a fast machine the flight can start before the poll
# arms the anchor, and the poll's overshoot is not deterministic.
SKIP_FRAMES=${SKIP_FRAMES-90}
f0=$(bh gdb "x/1hx $frames" | awk '/:/ {print $2}')
echo "frame counter at the first c2p seen: $((f0))" >> "$OUT/anchor.txt"
[ $((f0)) -le "$SKIP_FRAMES" ] || { echo "flight frame $((f0)) is past SKIP_FRAMES=$SKIP_FRAMES" >&2; exit 1; }
if [ $((f0)) -lt "$SKIP_FRAMES" ]; then
  bh gdb "break *$anchor
ignore \$bpnum $((SKIP_FRAMES - f0 - 1))
continue
delete" >> "$OUT/anchor.txt"
fi
bh gdb "x/1hx $frames" >> "$OUT/anchor.txt"
retain_log() { cp amiga/.run/fsuae.log "$OUT/fsuae.log"; }
# STATE_ONLY=1: dump memory at the c2p entry of flight frame SKIP_FRAMES and stop (game-state
# comparisons at equal frame numbers: the coupling test, docs/profiling.md §9).
if [ "${STATE_ONLY:-0}" = 1 ]; then
  dump
  bh quit > /dev/null; trap - EXIT
  retain_log
  exit 0
fi
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
