# Powerdrome hooks (common/template/game.sh lists them).

# Every build includes the generated sine table tmp/build/mouse-sine.i (tools/mouse_sine.py).
# The original builds assemble the reconstruction src/original/Powerdrome.s as the original
# was: without optimisation, and original without -pic. original must equal the installed slave.
game_build() {
  local build="$1" out="$2"
  mkdir -p tmp/build
  python3 tools/mouse_sine.py tmp/build/mouse-sine.i
  case "$build" in
    original|original_verify)
      SOURCE=src/original/Powerdrome.s
      VASM_FLAGS="-m68000 -no-opt -Fhunkexe -nosym"
      DEFINES_original="" DEFINES_original_verify="-DVERIFY=1"
      [ "$build" = original ] || VASM_FLAGS="-m68000 -no-opt -pic -Fhunkexe -nosym"
      ;;
  esac
  vasm_build "$build" "$out"
  if [ "$build" = original ] && [ -f "tmp/game/$GAME_DIR/$SLAVE_FILE" ]; then
    cmp "$out/$VARIANT.Slave" "tmp/game/$GAME_DIR/$SLAVE_FILE" ||
      die "the original build differs from tmp/game/$GAME_DIR/$SLAVE_FILE"
  fi
}

# WHD_SPLASH=1 shows WHDLoad's options and waits for Start.
game_prepare() {
  if [ "${WHD_SPLASH:-0}" = 1 ]; then WHD_DEFAULTS="PRELOAD SPLASHDELAY=-1"; fi
}
GAME_FSUAE_ARGS=(--window_width=760 --window_height=568)

# The reconstruction must still equal the installed slave, the VERIFY and coverage builds must
# assemble, and the host-side checks need no emulator.
game_check() {
  (
    cd "$GAME_ROOT"
    "$COMMON/build.sh" verify > /dev/null && echo "verify: builds"
    "$COMMON/build.sh" coverage > /dev/null && echo "coverage: builds"
    "$COMMON/build.sh" original_verify > /dev/null && echo "original_verify: builds"
    if [ -f "tmp/game/$GAME_DIR/$SLAVE_FILE" ]; then
      "$COMMON/build.sh" original > /dev/null && echo "original: equals the installed slave"
    else
      echo "skipped (no installed game; make unpack): the original build comparison"
    fi
    python3 tools/test_command_transport.py 2>&1 | tail -1
    if [ -f tmp/extracted/pd ]; then
      python3 tools/check_timing_layout.py > /dev/null && echo "check_timing_layout: passed"
    else
      echo "skipped (no tmp/extracted/pd): tools/check_timing_layout.py"
    fi
  )
}
