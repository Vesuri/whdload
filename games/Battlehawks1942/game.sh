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
# assemble, the release slave must leave BH original without CUSTOM2 (tools/pl_check.py),
# the Enhanced framerate routines must pass their Unicorn checks on the 68000 and 68040
# (tools/timing_check.py; tools/combat_check.py for step 3's timers and combat), step 4's
# rendering routines must equal BH's on the 68000 and 68020 (tools/render_check.py), and
# the tools must compile.
game_check() {
  (
    cd "$GAME_ROOT"
    local b
    for b in verify c2pfull tscale rectime mouse spancheck; do
      "$COMMON/build.sh" "$b" > /dev/null && echo "$b: builds"
    done
    "$COMMON/build.sh" release > /dev/null
    python3 tools/pl_check.py
    if [ -f "tmp/game/$GAME_DIR/$SLAVE_FILE" ]; then
      "$COMMON/build.sh" original > /dev/null && echo "original: equals the installed slave"
      local t
      for t in timing_check combat_check; do
        for b in 68000 68040; do
          python3 "tools/$t.py" --cpu "$b" > "tmp/$t-$b.log" ||
            { grep FAIL "tmp/$t-$b.log" | head -20; tail -1 "tmp/$t-$b.log"; exit 1; }
          echo "$t $b: $(tail -1 "tmp/$t-$b.log" | sed 's/^# //')"
        done
      done
      for b in 68000 68020; do
        python3 tools/render_check.py --cpu "$b" > "tmp/render_check-$b.log" ||
          { grep -A3 FAIL "tmp/render_check-$b.log" | head -20; exit 1; }
        echo "render_check $b: $(grep -c '^# ' "tmp/render_check-$b.log") routines equal"
      done
    else
      echo "skipped (no installed game; make unpack): the original build comparison," \
        "timing_check, combat_check, render_check"
    fi
    python3 -c 'import py_compile, sys; [py_compile.compile(f, doraise=True) for f in sys.argv[1:]]' tools/*.py &&
      echo "tools: compile"
    bash -n tools/fixed_window.sh && bash -n tools/record.sh && echo "fixed_window.sh, record.sh: parse"
  )
}
