# Gunship hooks (common/template/game.sh lists them).

# a500-fast, the default machine: the shared cycle-exact a500 (68000, 512 KB chip) with 8 MB
# Zorro II fast RAM and no slow RAM. EXTRA_ARGS goes first and FS-UAE keeps the first value
# of a repeated option, so the caller's FAST_KB or SLOW_KB replaces the matching default.
game_prepare() {
  [ "${AMIGA_SETUP:-}" = a500-fast ] || return 0
  local memory=""
  user_set FAST_KB || memory="--fast_memory=8192"
  user_set SLOW_KB || memory="$memory --slow_memory=0"
  AMIGA_SETUP=a500
  EXTRA_ARGS="$memory ${EXTRA_ARGS:-}"
  export AMIGA_SETUP EXTRA_ARGS
}

# The unit tests that need only the release and VERIFY builds (GAME_CHECKS) and, once
# make unpack has installed the drawers, the original executables (GAME_DATA_CHECKS). The
# other tools/test_*.py read captures left in tmp/ and are run by hand (docs/development.md).
GAME_CHECKS="test_verify_policy.py test_verify_frame.py test_verify_runtime_rng_c.py
  test_cockpit_e.py test_draw_overhead_d.py test_damage_colour.py test_damage_rotation.py
  test_demo_owner.py check_cpu_gate_f.py test_timing_fifo_owner_c.py test_timing_live_input_c.py"
GAME_DATA_CHECKS="test_blitter.py test_left_drift.py"

game_check() {
  (
    cd "$GAME_ROOT"
    "$COMMON/build.sh" verify > /dev/null
    tests="$GAME_CHECKS"
    if [ -d tmp/game/Gunship ] && [ -d tmp/game/GunshipNTSC ]; then
      tests="$tests $GAME_DATA_CHECKS"
    else
      echo "skipped (no installed drawers; make unpack): $GAME_DATA_CHECKS"
    fi
    for test in $tests; do
      log="tmp/check-${test%.py}.log"
      python3 "tools/$test" > "$log" 2>&1 || { cat "$log" >&2; die "tools/$test failed ($log)"; }
      echo "passed: tools/$test"
    done
  )
}
