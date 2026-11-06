# Test Drive II hooks (common/template/game.sh lists them).

# TD_SETUP=a500|a1200|a1200-030: the reference machines every capture in docs/ was made on.
# a500: 68000, 512 KB chip, 1.5 MB slow RAM; a1200: 68EC020, 2 MB chip, 4 MB fast, the
# A1200 Kickstart; a1200-030: that with a cycle-exact 25 MHz 68030 (an accelerated A1200).
# Not with a named SETUP.
game_prepare() {
  case "${TD_SETUP:-}" in
    '') return 0 ;;
    a500|a1200|a1200-030) ;;
    *) die "unknown TD_SETUP: $TD_SETUP (a500, a1200 or a1200-030)" ;;
  esac
  [ -z "${AMIGA_SETUP:-}" ] || die "use TD_SETUP or SETUP, not both"
  AMIGA_MODEL=A500 CPU=68000 CHIP_KB=512 FAST_KB=0 SLOW_KB=1536
  if [ "$TD_SETUP" != a500 ]; then
    AMIGA_MODEL=A1200 CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 SLOW_KB=0
    KICKSTART="$KICKSTART_A1200"
  fi
  if [ "$TD_SETUP" = a1200-030 ]; then
    CPU=68030
    EXTRA_ARGS="--uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true ${EXTRA_ARGS:-}"
  fi
  export AMIGA_MODEL CPU CHIP_KB FAST_KB SLOW_KB KICKSTART EXTRA_ARGS
}

# The installer's source/ also ships the KickEmu sources and API headers the slave is built
# from, which come from $WHDLOAD, outside the game: they are staged in tmp/release/whdload/
# for release/release.json, then the shared packager makes the archive and its checks.
game_dist() {
  local dist="$1" f stage="$GAME_ROOT/tmp/release/whdload" force=()
  rm -rf "$stage"
  for f in Include/whdload.i Include/whdmacros.i Src/sources/whdload/kick13.s \
           Src/sources/whdload/kickfs.s Src/sources/whdload/segtracker.s \
           Src/sources/whdload/kick.readme; do
    [ -f "$WHDLOAD/$f" ] || die "no $WHDLOAD/$f"
    mkdir -p "$stage/$(dirname "$f")"
    cp "$WHDLOAD/$f" "$stage/$f"
  done
  [ "${FORCE:-0}" != 1 ] || force=(--force)
  python3 "$COMMON/tools/package_release.py" --game-root "$GAME_ROOT" --dist "$dist" \
    --variants "$VARIANTS" ${force[@]+"${force[@]}"}
}

# Every tool compiles, the VERIFY build assembles, and, with the game installed, the
# simulation hook audit passes. The capture checks read evidence in tmp/ and are run by hand
# (docs/testing.md, "Regression checklist").
game_check() {
  (
    cd "$GAME_ROOT"
    python3 - <<'EOF' || die "a tool does not compile"
import pathlib, sys
bad = 0
for p in sorted(pathlib.Path('tools').glob('*.py')):
    try:
        compile(p.read_text(), str(p), 'exec')
    except SyntaxError as e:
        print(f'{p}: {e}', file=sys.stderr); bad = 1
sys.exit(bad)
EOF
    echo "compiled: tools/*.py"
    bash -n tools/fixed_window.sh tools/profile_demo.sh || die "a tool script does not parse"
    echo "parsed: tools/*.sh"
    "$COMMON/build.sh" verify > /dev/null && echo "verify: builds"
    if [ -f "tmp/game/$GAME_DIR/data/duel" ]; then
      log=tmp/check-audit_simulation.log
      python3 tools/audit_simulation.py "tmp/game/$GAME_DIR/data/duel" > "$log" 2>&1 ||
        { cat "$log" >&2; die "tools/audit_simulation.py failed ($log)"; }
      echo "passed: tools/audit_simulation.py ($(tail -1 "$log"))"
    else
      echo "skipped (no installed game; make unpack): tools/audit_simulation.py"
    fi
  )
}
