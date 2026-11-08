# Mercenary 3 hooks (common/template/game.sh lists them).

# Each archive goes to its extraction directory in manifest/inputs.json: the installed game
# (with its own top drawer) under tmp/game/, the official installer, with the original
# source, under tmp/installer/. tools/check_inputs.py then checks every extracted file.
game_unpack() {
  local name target
  for name in Mercenary3_v1.2_0356.lha:tmp/game/Mercenary3_v1.2_0356 \
      Mercenary3.lha:tmp/installer/Mercenary3; do
    target="${name#*:}" name="${name%%:*}"
    if [ -e "$target" ]; then
      if [ "${FORCE:-0}" = 1 ]; then rm -rf "$target"; else
        echo "kept the existing $target (FORCE=1 replaces it)"; continue
      fi
    fi
    mkdir -p "$target"
    "$LHA" "xqw=$target" "tmp/archives/$name"
    echo "unpacked $target"
  done
  python3 tools/check_inputs.py
}

# The rebuilt original slave must equal the installed one byte for byte.
game_original() {
  (cd "$GAME_ROOT" &&
    env -u GAME_DIR -u SLAVE_FILE -u SOURCE VARIANT=Mercenary3-original "$COMMON/build.sh" release > /dev/null &&
    cmp tmp/build/release/Mercenary3-original.Slave "tmp/game/$GAME_DIR/$SLAVE_FILE") &&
    echo "original: identical to the shipped slave"
}

# The installer archive with the release slave, a new ReadMe and CUSTOM5=1 in the game
# icons (tools/package_release.py). The inputs, the original and the VERIFY build are
# checked first, as before every release.
game_dist() {
  local force=()
  [ "${FORCE:-0}" != 1 ] || force=(--force)
  (cd "$GAME_ROOT" && python3 tools/check_inputs.py) &&
    game_original &&
    (cd "$GAME_ROOT" &&
      env -u GAME_DIR -u SLAVE_FILE -u SOURCE VARIANT=Mercenary3 "$COMMON/build.sh" verify > /dev/null &&
      python3 tools/package_release.py --slave tmp/build/release/Mercenary3.Slave \
        --dist "$1" ${force[@]+"${force[@]}"})
}

# The pinned inputs, the original, and the unit tests (they read the installed slave).
game_check() {
  (cd "$GAME_ROOT" && python3 tools/check_inputs.py) &&
    game_original &&
    (cd "$GAME_ROOT" && python3 -m unittest discover -s tools -p 'test_*.py' -q)
}

# SAVES=<directory> (absolute, or relative to the game directory): put its saved games
# (Mercenary3.save0..9) on the run's game drive, for checks that start from a saved
# situation (tools/replay_trace.py, tools/presentation_check.py).
game_drives() {
  [ -n "${SAVES:-}" ] || return 0
  local dir="$SAVES"
  case "$dir" in /*) ;; *) dir="$GAME_ROOT/$dir" ;; esac
  [ -d "$dir" ] || die "no saves directory $dir"
  cp -f "$dir"/Mercenary3.save[0-9] "$2/"
}
