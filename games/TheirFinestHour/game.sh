# Their Finest Hour hooks (common/template/game.sh lists them).

# Psygore's two v1.1 archives with the new slave, ReadMe, launch icons (CUSTOM2=1) and
# installer: more than release.json describes (tools/package_release.py).
game_dist() {
  (cd "$GAME_ROOT" && python3 tools/package_release.py --dist "$1")
}

# The CPU-only timing regressions (docs/framerate-audit.md) need a local fast-memory flight
# capture: CAPTURE=<code.bin>, at CAPTURE_BASE (default 0x200000). Without one they are
# skipped; the emulator-driven checks are run by hand (docs/development.md).
game_check() {
  local capture="$GAME_ROOT/tmp/input-combat/bomb-smoke/code.bin" cpu
  [ -z "${CAPTURE:-}" ] || capture="$(caller_path "$CAPTURE")"
  if [ ! -f "$capture" ]; then
    echo "$GAME: timing regressions skipped (no capture; CAPTURE=<code.bin> runs them)"
    return 0
  fi
  (cd "$GAME_ROOT" && for cpu in 68000 68040; do
    python3 tools/timing_audit_check.py "$capture" "${CAPTURE_BASE:-0x200000}" \
      tmp/build/release/TheirFinestHour.Slave tmp/build/release/TheirFinestHour.lst \
      --cpu "$cpu" > "tmp/timing-audit-$cpu.log" ||
      { tail -20 "tmp/timing-audit-$cpu.log" >&2; die "timing regressions failed on $cpu (tmp/timing-audit-$cpu.log)"; }
    echo "$GAME: timing regressions pass on $cpu"
  done)
}
