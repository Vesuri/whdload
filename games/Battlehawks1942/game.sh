# Battlehawks 1942 hooks (common/template/game.sh lists them).

# The original build assembles the reconstruction src/original/Battlehawks1942.s without
# optimisation (-no-opt: vasm must not re-choose encodings the shipped slave did not use) and
# must equal the installed slave.
game_build() {
  local build="$1" out="$2"
  if [ "$build" = original ]; then
    SOURCE=src/original/Battlehawks1942.s
    VASM_FLAGS="$VASM_FLAGS -no-opt"
  fi
  vasm_build "$build" "$out"
  if [ "$build" = original ] && [ -f "tmp/game/$GAME_DIR/$SLAVE_FILE" ]; then
    cmp "$out/$VARIANT.Slave" "tmp/game/$GAME_DIR/$SLAVE_FILE" ||
      die "the original build differs from tmp/game/$GAME_DIR/$SLAVE_FILE"
  fi
}

# PLAYBACK=file replays an FS-UAE input recording (tools/splice_rec.py). FS-UAE appends to
# the file it plays and rewrites it on exit, so it plays a copy. This FS-UAE build does not
# replay (docs/profiling.md §3); kept for one that does.
game_drives() {
  [ -n "${PLAYBACK:-}" ] || return 0
  cp -f "$(caller_path "$PLAYBACK")" "$FSUAE_RUN/playback.rec"
  GAME_FSUAE_ARGS+=(--record="$PWD/$FSUAE_RUN/playback.rec" --deterministic=1)
}

# The reconstruction must still equal the installed slave, the instrumented builds must
# assemble, and the tools must compile.
game_check() {
  (
    cd "$GAME_ROOT"
    local b
    for b in verify c2pfull tscale; do
      "$COMMON/build.sh" "$b" > /dev/null && echo "$b: builds"
    done
    if [ -f "tmp/game/$GAME_DIR/$SLAVE_FILE" ]; then
      "$COMMON/build.sh" original > /dev/null && echo "original: equals the installed slave"
    else
      echo "skipped (no installed game; make unpack): the original build comparison"
    fi
    python3 -c 'import py_compile, sys; [py_compile.compile(f, doraise=True) for f in sys.argv[1:]]' tools/*.py &&
      echo "tools: compile"
    bash -n tools/fixed_window.sh && echo "fixed_window.sh: parses"
  )
}
