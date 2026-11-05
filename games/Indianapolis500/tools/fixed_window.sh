#!/usr/bin/env bash
# Benchmark window: trace FIELDS PAL fields of the attract demo from its first frame.
# tools/fixed_window.sh OUTDIR [SLAVE]
# The anchor is the first execution since boot of game:0b57e, the renderer's end-of-frame
# (it sets the swap-request bit for the VBL handler).  The title/credits never reach it, so
# the first hit is the end of the demo's first frame.  SKIP_FRAMES=N starts the window N
# frame-ends later instead (other demo camera views).  ANCHOR overrides the hunk offset.
set -euo pipefail
cd "$(dirname "$0")/.."
# common/run.sh runs each instance in tmp/run/<INSTANCE>/.
RUN="tmp/run/${INSTANCE:-default}/.run"; mkdir -p "$RUN"
OUT=$1; mkdir -p "$OUT"; FIELDS=${FIELDS:-100}
export CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" EXTRA_ARGS="${EXTRA_ARGS---slow_memory=1536}"
# The game reads the port-0 mouse counters (JOY0DAT, game:0b424); a host mouse over the
# window would change them, so captures run with nothing in port 0.
export JOY0="${JOY0:-none}"
# Retain exactly the slave used by this capture; later builds must not change
# region sizes or hook addresses when analysing a saved trace.
INPUT_SLAVE=${2:-tmp/game/Indianapolis500/Indianapolis500.Slave}
if [ "$INPUT_SLAVE" != "$PWD/$OUT/slave.slave" ]; then
  cp "$INPUT_SLAVE" "$OUT/slave.slave"
fi
export DETERMINISTIC=1 SLAVE="$PWD/$OUT/slave.slave" CPU="${CPU:-68000}"
# The code is loaded into "other" memory: fast RAM at $200000 when there is any, else slow
# RAM, else chip RAM.
SLOW_KB=$(sed -n 's/.*--slow_memory=\([0-9]*\).*/\1/p' <<< "$EXTRA_ARGS")
if [ "$FAST_KB" -gt 0 ]; then BASE=0x200000; SIZE=$((FAST_KB * 1024))
elif [ "${SLOW_KB:-512}" -gt 0 ]; then BASE=0xc00000; SIZE=$((${SLOW_KB:-512} * 1024))
else BASE=0x0; SIZE=$((CHIP_KB * 1024)); fi   # chip only (stock A1200)
# Cache only the address, keyed by machine, arguments and slave build. A calibration
# boot discovers it; the measurement boot arms the anchor breakpoint at CPU reset.
mkdir -p tmp/cache
KEY=$(python3 -c 'import hashlib,os; from pathlib import Path; p=os.environ.get("SLAVE") or "tmp/game/Indianapolis500/Indianapolis500.Slave"; h=hashlib.sha256(Path(p).read_bytes()); h.update(repr([(k,os.environ.get(k)) for k in ("AMIGA_MODEL","KICKSTART","CPU","CHIP_KB","FAST_KB","EXTRA_ARGS","WHD_ARGS")]).encode()); print(h.hexdigest()[:20])')
CACHE="tmp/cache/hunk-$KEY.txt"
BOOT_HUNK=${BOOT_HUNK:-$(cat "$CACHE" 2>/dev/null || true)}
if [ -n "$BOOT_HUNK" ]; then export BOOT_BREAK=$(printf '%#x' $((BOOT_HUNK + ${ANCHOR:-0xb57e}))); fi
i500() { python3 tools/i500.py "$@"; }
retain_log() {
  cp "$RUN"/fsuae.log "$OUT/fsuae-stdout.log"
  local logfile
  logfile=$(sed -n 's/^LOGFILE: //p' "$RUN"/fsuae.log | tail -1)
  if [ -n "$logfile" ] && [ -f "$logfile" ]; then
    cp "$logfile" "$OUT/fsuae.log"
  else
    cp "$RUN"/fsuae.log "$OUT/fsuae.log"
  fi
}
[ -S "$RUN"/i500.sock ] && { i500 quit > /dev/null 2>&1 || true; sleep 1; }
rm -f "$RUN"/serve.log "$OUT/trace.bin"
WARP=1 python3 tools/i500.py serve > "$RUN"/serve.log 2>&1 &
trap 'i500 quit > /dev/null 2>&1 || true' EXIT
SERVER=$!
for _ in $(seq 1 "${SERVE_WAIT:-180}"); do
  grep -q serving "$RUN"/serve.log 2>/dev/null && break
  kill -0 "$SERVER" 2>/dev/null || { cat "$RUN"/serve.log >&2; exit 1; }
  sleep 1
done
grep -q serving "$RUN"/serve.log || { echo "anchor breakpoint not reached" >&2; exit 1; }

# The dump occasionally fails to appear (seen on A1200 configs); retry and show gdb's reply.
dump() {
  local reply
  for _ in $(seq 1 12); do
    # Harness-relative (gdb runs here and cannot quote paths), never a shared /tmp name.
    reply=$(i500 gdb "dump binary memory tmp/i500-code.bin $BASE $(printf '%#x' $((BASE + SIZE)))")
    [ -f tmp/i500-code.bin ] && { mv tmp/i500-code.bin "$OUT/code.bin"; return 0; }
    echo "memory not ready, retrying: ${reply: -300}" >&2
    kill -0 "$(cat "$RUN"/fsuae.pid)" 2>/dev/null || return 1
    i500 wait 1 > /dev/null
  done
  return 1
}
hunk=
for _ in $(seq 1 60); do
  [ -n "$BOOT_HUNK" ] || i500 wait 1 > /dev/null
  dump
  hunk=$(python3 -c "
import sys; sys.path.insert(0, 'tools'); from i500_report import regions
r = {n: lo for lo, hi, n, o in regions(open('$OUT/code.bin', 'rb').read(), $BASE)}
print(hex(r['game']) if 'game' in r else '')")
  [ -n "$hunk" ] && break
done
[ -n "$hunk" ] || { echo "game never appeared in memory" >&2; exit 1; }
echo "game code hunk at $hunk"
if [ -z "$BOOT_HUNK" ]; then
  printf '%s\n' "$hunk" > "$CACHE"
  i500 quit > /dev/null; trap - EXIT
  echo "calibrated code address; rebooting with the anchor breakpoint armed"
  exec bash "$0" "$OUT" "$SLAVE"
fi
[ "$((hunk))" = "$((BOOT_HUNK))" ] || { echo "loaded hunk differs from boot breakpoint" >&2; exit 1; }
i500 gdb 'info registers pc sp' > "$OUT/anchor.txt"
if [ "${SKIP_FRAMES:-0}" -gt 0 ]; then
  i500 gdb "break *$(printf '%#x' $((hunk + ${ANCHOR:-0xb57e})))
ignore \$bpnum $((SKIP_FRAMES - 1))
continue
delete" >> "$OUT/anchor.txt"
fi
# Replay fixtures (DRIVING_REPLAY builds): the first transition wipe's length in fixture CIA
# ticks, from view style 1 -> 2 (game:00190) to its end (game:001b0). Runs before DRIVING_TICK.
if [ "${WIPE_TICKS:-0}" = 1 ]; then
  python3 - "$OUT/code.bin" "$BASE" <<'PYWIPE' | tee "$OUT/wipe.txt"
import sys
from pathlib import Path
sys.path.insert(0,'tools')
from i500_report import regions
from state_fields import command
b=Path(sys.argv[1]).read_bytes();base=int(sys.argv[2],0)
r={n:(lo,hi) for lo,hi,n,o in regions(b,base)};lo,hi=r['slave'];m=b.find(b'I5DR',lo-base,hi-base);assert m>=0,'DRIVING_TEST build required'
g=r['game'][0];counter=base+m+4
reply=command(f'break *{g+0x190:#x}\ncontinue\ndelete\nprintf "wipe start %u\\n", *(unsigned int *){counter:#x}\nbreak *{g+0x1b0:#x}\ncontinue\ndelete\nprintf "wipe end %u\\n", *(unsigned int *){counter:#x}')
start=int(reply.split('wipe start ')[1].split()[0]);end=int(reply.split('wipe end ')[1].split()[0])
print(f'wipe start {start}, end {end}: {end-start} CIA ticks')
PYWIPE
fi
# Driving fixtures use their native-input CIA counter, not the demo director. The wait stops
# at DRIVING_BREAK (default the cockpit frame hook game:00270; 0x26d4c for replays).
if [ -n "${DRIVING_TICK:-}" ]; then
  python3 - "$OUT/code.bin" "$BASE" "$DRIVING_TICK" "${DRIVING_BREAK:-0x270}" <<'PYDRIVE'
import sys
from pathlib import Path
sys.path.insert(0,'tools')
from i500_report import regions
from state_fields import command
b=Path(sys.argv[1]).read_bytes();base=int(sys.argv[2],0);tick=int(sys.argv[3]);assert tick>=0
r={n:(lo,hi) for lo,hi,n,o in regions(b,base)};lo,hi=r['slave'];m=b.find(b'I5DR',lo-base,hi-base);assert m>=0,'DRIVING_TEST build required'
g=r['game'][0];counter=base+m+4
reply=command(f'break *{g+int(sys.argv[4],0):#x}\nwhile *(unsigned int *){counter:#x} < {tick}\ncontinue\nend\ndelete\nprintf "Driving fixture CIA ticks: %u\\n", *(unsigned int *){counter:#x}')
Path(sys.argv[1]).with_name('driving-anchor.txt').write_text(reply)
# gdb's loop prompts (' > >') can precede the line when the loop body never runs.
print(next(line[line.index('Driving'):] for line in reply.splitlines() if 'Driving fixture CIA ticks:' in line))
PYDRIVE
fi
# Tick-aligned per-view windows: director counter runs 0..899 in the demo.
# Use 50,200,350,500,650,800 for windows inside all six camera segments.
# Breakpoint conditions are evaluated by gdb; game memory stays read-only.
if [ -n "${DEMO_TICK:-}" ]; then
  [ "$DEMO_TICK" -ge 0 ] && [ "$DEMO_TICK" -lt 900 ] || { echo "DEMO_TICK must be 0..899" >&2; exit 1; }
  i500 gdb "break *$(printf '%#x' $((hunk + 0x7ee)))
continue
while *(unsigned short *)$(printf '%#x' $((hunk + 0x268d0))) != $DEMO_TICK
continue
end
delete" >> "$OUT/anchor.txt"
fi
# VERIFY-only twin comparisons use counters rather than frame-rate instruments.
if [ "${PIXEL_FRAMES:-0}" -gt 0 ]; then
  python3 tools/pixel_frames.py "$PIXEL_FRAMES" "$OUT/pixels" "$OUT/code.bin" "$BASE"
  dump
  i500 quit > /dev/null; trap - EXIT
  retain_log
  exit 0
fi
# Multiple read-only windows share one deterministic boot. The Python driver
# validates each director anchor; the emulator remains owned by this shell.
if [ -n "${DEMO_TICKS:-}" ]; then
  python3 tools/view_windows.py "$FIELDS" "$OUT" "$BASE" "$DEMO_TICKS"
  i500 quit > /dev/null; trap - EXIT
  retain_log
  exit 0
fi
# HOLD=1 leaves the emulator stopped at the window start for manual gdb work
# (python3 tools/i500.py gdb '...'); end it with python3 tools/i500.py quit.
if [ "${HOLD:-0}" = 1 ]; then
  dump; trap - EXIT
  echo "holding at the window start; python3 tools/i500.py quit when done"
  exit 0
fi
# Optional read-only state study: sample N VBL (or STATE_AT=soft) entries.
# The trace then starts after these N fields; record that offset when quoting its fps.
if [ "${STATE_FIELDS:-0}" -gt 0 ]; then
  python3 tools/state_fields.py "$STATE_FIELDS" "$OUT/state" "$OUT/code.bin" "$BASE"
fi
if [ "${MOTION_FRAMES:-0}" -gt 0 ]; then
  python3 tools/motion_frames.py "$MOTION_FRAMES" "$OUT/motion" "$OUT/code.bin" "$BASE"
  dump
  i500 quit > /dev/null; trap - EXIT
  retain_log
  exit 0
fi
if [ "${SOFT_TICKS:-0}" -gt 0 ]; then
  python3 tools/soft_timing.py "$SOFT_TICKS" "$OUT/soft" "$OUT/code.bin" "$BASE"
  i500 quit > /dev/null; trap - EXIT
  retain_log
  exit 0
fi
if [ "${TIMING_FRAMES:-0}" -gt 0 ]; then
  python3 tools/timing_frames.py "$TIMING_FRAMES" "$OUT/timing" "$OUT/code.bin" "$BASE"
  i500 quit > /dev/null; trap - EXIT
  retain_log
  exit 0
fi
# State-only studies need no cycle trace or debugger attach to the host process.
# Deliberately emit no frame-rate figure in this mode.
if [ "${STATE_ONLY:-0}" = 1 ]; then
  [ "${STATE_FIELDS:-0}" -gt 0 ] || { echo "STATE_ONLY requires STATE_FIELDS" >&2; exit 1; }
  dump
  i500 quit > /dev/null; trap - EXIT
  retain_log
  echo "state-only capture complete (no frame-rate measurement)"
  exit 0
fi
if [ "${SWAP_ONLY:-0}" = 1 ]; then
  python3 tools/swap_fields.py "$FIELDS" "$OUT" "$OUT/code.bin" "$BASE"
  if [ "${DRIVING_FRAMES:-0}" -gt 0 ]; then
    python3 tools/driving_frames.py "$DRIVING_FRAMES" "$OUT/driving" "$OUT/code.bin" "$BASE"
  fi
  dump
  i500 quit > /dev/null; trap - EXIT
  retain_log
  exit 0
fi
reply=$(i500 profile "$FIELDS" "$PWD/$OUT/trace.bin")
[ -f "$OUT/trace.bin" ] || { echo "no trace: $reply" >&2; exit 1; }
dump
i500 quit > /dev/null; trap - EXIT
retain_log
python3 - "$OUT" <<'EOF'
import sys; sys.path.insert(0, 'tools'); import _amigaxdev; from amigaxdev import barto
out = sys.argv[1]; t = barto.load(f'{out}/trace.bin')
open(f'{out}/first.png', 'wb').write(t.fields[0].shot)
open(f'{out}/last.png', 'wb').write(t.fields[-1].shot)
EOF
python3 tools/frames.py "$OUT/trace.bin" "$OUT/code.bin" "$BASE" | tee "$OUT/frames.txt"
