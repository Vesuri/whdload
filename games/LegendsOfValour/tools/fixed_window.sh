#!/usr/bin/env bash
# Benchmark window: trace FIELDS PAL fields from the input tape's anchor (an entry marked A,
# whdload/tape.s _tape_anchor).  Default route tools/tapes/spin.txt: default character,
# large view, 250 fields into turning right on the spot.
#   tools/fixed_window.sh OUTDIR [TAPE.txt]
# Builds the VERIFY slave and keeps it (OUT/slave.slave + listing) with the capture; analyse
# with SLAVE=$OUT/slave.slave.  One boot: the slave is in memory long before the anchor, so
# its address is found from a dump and the anchor breakpoint armed in the same boot.
#   FIELDS=100      fields traced          STATE_ONLY / SWAP_ONLY as in Test Drive II
#   CHIP_KB/FAST_KB/EXTRA_ARGS/CPU/AMIGA_MODEL/KICKSTART: machine (default A500-equivalent)
set -euo pipefail
cd "$(dirname "$0")/.."
export FSUAE_RUN="${FSUAE_RUN:-.cap}"; CAP=$FSUAE_RUN; mkdir -p "amiga/$CAP"
OUT=$1; mkdir -p "$OUT"; FIELDS=${FIELDS:-100}; TAPE_TXT=${2:-tools/tapes/spin.txt}
export CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" EXTRA_ARGS="${EXTRA_ARGS---slow_memory=1536}"
if [ -z "${KEEP_SLAVE:-}" ]; then
  if [ "${PROFILE_WINDOW:-}" = guest ]; then
    make -s -C whdload verify VASMFLAGS="${VASMFLAGS:-} -DPROFILER_WINDOW=1" > /dev/null
  else
    make -s -C whdload verify > /dev/null
  fi
  cp tmp/build/LegendsOfValour.Slave "$OUT/slave.slave"
  cp tmp/build/LegendsOfValour.lst "$OUT/slave.lst"
fi
python3 tools/tape.py "$TAPE_TXT" "$OUT/tape.bin" > /dev/null
cp "$TAPE_TXT" "$OUT/tape.txt"
export DETERMINISTIC=1 SLAVE="$PWD/$OUT/slave.slave" TAPE="$PWD/$OUT/tape.bin" CPU="${CPU:-68000}" \
  JOY0=none WHD_ARGS="CUSTOM5=${TAPE_OPTIONS:-1} ${WHD_ARGS:-}"
sym() { python3 -c "
import re, sys
for l in open('$OUT/slave.lst', errors='replace'):
    m = re.match(r'^$1\s+00:([0-9A-F]{8})\s*$', l)
    if m: print(hex(int(m.group(1), 16))); break"; }
ANCHOR=$(sym _tape_anchor)
if [ "${PROFILE_WINDOW:-}" = guest ]; then ANCHOR=$(sym _profile_ready); fi
TAPEFIELD=$(sym _tapefield); H11=$(sym _h11)
[ -n "$ANCHOR" ] && [ -n "$TAPEFIELD" ] || { echo "no _tape_anchor in $OUT/slave.lst" >&2; exit 1; }
# The code is loaded into "other" memory: fast RAM at $200000 when there is any, else slow RAM.
SLOW_KB=$(sed -n 's/.*--slow_memory=\([0-9]*\).*/\1/p' <<< "$EXTRA_ARGS")
if [ "$FAST_KB" -gt 0 ]; then BASE=0x200000; SIZE=$((FAST_KB * 1024))
else BASE=0xc00000; SIZE=$((${SLOW_KB:-512} * 1024)); fi
lov() { python3 tools/lov.py "$@"; }
retain_log() {
  cp amiga/$CAP/fsuae.log "$OUT/fsuae-stdout.log"
  local logfile
  logfile=$(sed -n 's/^LOGFILE: //p' amiga/$CAP/fsuae.log | tail -1)
  if [ -n "$logfile" ] && [ -f "$logfile" ]; then cp "$logfile" "$OUT/fsuae.log"; fi
}
[ -S amiga/$CAP/lov.sock ] && { lov quit > /dev/null 2>&1 || true; sleep 1; }
rm -f amiga/$CAP/serve.log "$OUT/trace.bin"
WARP=1 python3 tools/lov.py serve > amiga/$CAP/serve.log 2>&1 &
trap 'lov quit > /dev/null 2>&1 || true' EXIT
SERVER=$!
for _ in $(seq 1 "${SERVE_WAIT:-180}"); do
  grep -q serving amiga/$CAP/serve.log 2>/dev/null && break
  kill -0 "$SERVER" 2>/dev/null || { cat amiga/$CAP/serve.log >&2; exit 1; }
  sleep 1
done
grep -q serving amiga/$CAP/serve.log || { echo "server did not start" >&2; exit 1; }

dump() { lov gdb "dump binary memory /tmp/lov-code-$$.bin $BASE $(printf '%#x' $((BASE + SIZE)))" > /dev/null; mv /tmp/lov-code-$$.bin "$OUT/code.bin"; }
region() { python3 -c "
import sys; sys.path.insert(0, 'tools'); from lov_report import regions
r = {n: lo for lo, hi, n, o in regions(open('$OUT/code.bin', 'rb').read(), $BASE)}
print(hex(r['$1']) if '$1' in r else '')"; }
slave=
for scan_pass in $(seq 1 60); do
  # BOOT_BREAK leaves startup paused so abort breakpoints can be armed before
  # VERIFY unit tests run. Inspect that first stopped state without resuming it.
  if [ "$scan_pass" -ne 1 ] || [ -z "${BOOT_BREAK:-}" ]; then
    lov wait 0.5 > /dev/null
  fi
  # Keep the emulator stopped while scanning a large expansion-memory dump.
  # The gdb command otherwise resumes it and can pass the one-time tape anchor.
  lov stop > /dev/null
  dump
  slave=$(region slave)
  [ -n "$slave" ] && break
done
[ -n "$slave" ] || { echo "live slave never appeared in memory" >&2; exit 1; }
echo "slave at $slave, anchor $(printf '%#x' $((slave + ANCHOR)))"
ABORT=$(sym _c2p_abort)
BREAKS=("$(printf '%#x' $((slave + ANCHOR)))")
[ -z "$ABORT" ] || BREAKS+=("$(printf '%#x' $((slave + ABORT)))")
{ echo "slave $slave"; lov until "${BREAKS[@]}"; } > "$OUT/anchor.txt"
if [ -n "$ABORT" ] && grep -qi "$(printf '0x%08x' $((slave + ABORT)))" "$OUT/anchor.txt"; then
  lov gdb 'x/s $a0' >> "$OUT/anchor.txt"
  lov gdb 'info registers' > "$OUT/failure-registers.txt"
  dump; retain_log
  cat "$OUT/anchor.txt" >&2; exit 1
fi
if ! grep -Eq "^Breakpoint [0-9]+, 0x0*$(printf '%x' $((slave + ANCHOR)))[[:space:]]" "$OUT/anchor.txt"; then
  dump; retain_log
  cat "$OUT/anchor.txt" >&2
  echo "tape anchor breakpoint was not reached" >&2; exit 1
fi
if [ "${PROFILE_WINDOW:-}" = guest ]; then
  RESTORED=$(sym _profile_restored)
  [ -n "$RESTORED" ] || { echo "profiler restoration symbol missing" >&2; exit 1; }
  lov gdb 'maintenance packet qOffsets' > "$OUT/profiler-window.txt"
  grep -q 'received: "00001018"' "$OUT/profiler-window.txt" || {
    echo "profiler metadata query failed" >&2; exit 1;
  }
  lov until "$(printf '%#x' $((slave + RESTORED)))" >> "$OUT/profiler-window.txt"
  grep -Eq "^Breakpoint [0-9]+, 0x0*$(printf '%x' $((slave + RESTORED)))[[:space:]]" "$OUT/profiler-window.txt" || {
    echo "profiler metadata restoration was not reached" >&2; exit 1;
  }
fi
# The tape's field count is fixed by the script; the game's own field counter (h11:0602c)
# and its position (the hunks' addresses) show whether the boot took the same course.
h11=$(lov gdb "x/1xw $(printf '%#x' $((slave + H11)))" | awk '{print $2}')
{ lov gdb "x/1uw $(printf '%#x' $((slave + TAPEFIELD)))" | sed 's/^/tapefield /'
  lov gdb "x/1uw $(printf '%#x' $((h11 + 0x602c)))" | sed 's/^/gamefield /'
  echo "h11 $h11"; } >> "$OUT/anchor.txt"
cat "$OUT/anchor.txt"
# Refresh after decrunching: the early slave-location dump need not contain game hunks.
dump
if [ "${PROFILE_WINDOW:-}" = guest ]; then
  lov gdb "dump binary memory /tmp/lov-profiler-chip-$$.bin 0x1000 0x1020" > /dev/null
  mv /tmp/lov-profiler-chip-$$.bin "$OUT/profiler-chip.bin"
  PROFSTATE=$(sym _profile_state)
  proftask=$(lov gdb "x/1xw $(printf '%#x' $((slave + PROFSTATE + 2)))" | awk '{print $2}')
  lov gdb "dump binary memory /tmp/lov-profiler-task-$$.bin $(printf '%#x' $((proftask + 128))) $(printf '%#x' $((proftask + 144)))" > /dev/null
  mv /tmp/lov-profiler-task-$$.bin "$OUT/profiler-task.bin"
  python3 tools/profile_window_check.py "$OUT" --base "$BASE"
fi
if [ "${SELFTEST_FRAMES:-0}" -gt 0 ]; then
  DONE=$(sym _c2p_test_done)
  [ -n "$DONE" ] || { echo "pixel-twin symbol missing" >&2; exit 1; }
  lov gdb "break *$(printf '%#x' $((slave + ABORT)))
break *$(printf '%#x' $((slave + DONE)))
ignore \$bpnum $((SELFTEST_FRAMES - 1))
continue
info registers pc
delete" > "$OUT/selftest-gdb.txt"
  if grep -qi "$(printf '0x%08x' $((slave + ABORT)))" "$OUT/selftest-gdb.txt"; then
    lov gdb 'x/s $a0' >> "$OUT/selftest-gdb.txt"
    lov gdb 'info registers' > "$OUT/failure-registers.txt"
    dump; retain_log
    cat "$OUT/selftest-gdb.txt" >&2; exit 1
  fi
  if ! grep -Eq "^pc[[:space:]]+0x0*$(printf '%x' $((slave + DONE)))[[:space:]]" "$OUT/selftest-gdb.txt"; then
    cat "$OUT/selftest-gdb.txt" >&2
    echo "pixel-twin frame-count breakpoint was not reached" >&2; exit 1
  fi
  dump
  lov shot "$PWD/$OUT/selftest.png" > /dev/null
  lov quit > /dev/null; trap - EXIT; retain_log
  python3 tools/c2p_check.py "$OUT" --base "$BASE"
  exit 0
fi
if [ "${STATE_FIELDS:-0}" -gt 0 ]; then
  python3 tools/state_fields.py "$STATE_FIELDS" "$OUT/state" "$OUT/code.bin" "$BASE"
fi
if [ "${STATE_ONLY:-0}" = 1 ]; then
  dump; lov quit > /dev/null; trap - EXIT; retain_log
  echo "state-only capture complete (no frame-rate measurement)"; exit 0
fi
if [ "${SWAP_ONLY:-0}" = 1 ]; then
  python3 tools/swap_fields.py "$FIELDS" "$OUT" "$OUT/code.bin" "$BASE"
  dump; lov quit > /dev/null; trap - EXIT; retain_log; exit 0
fi
reply=$(lov profile "$FIELDS" "$PWD/$OUT/trace.bin")
[ -f "$OUT/trace.bin" ] || { echo "no trace: $reply" >&2; exit 1; }
dump
lov quit > /dev/null; trap - EXIT
retain_log
python3 - "$OUT" <<'EOF'
import sys; sys.path.insert(0, 'tools'); import barto
out = sys.argv[1]; t = barto.load(f'{out}/trace.bin')
open(f'{out}/first.png', 'wb').write(t.fields[0].shot)
open(f'{out}/last.png', 'wb').write(t.fields[-1].shot)
EOF
