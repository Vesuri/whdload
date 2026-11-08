# Legends of Valour hooks (common/template/game.sh lists them).

# One slave for the English, German and French AMIGA2: every game offset is an hN_OFFSET
# symbol (src/offsets.s) that depends on LOV_LANG. Assemble the slave once per language,
# turn the words that differ into the fixup table (tools/fixups.py) and append it to the
# English build; the slave applies it at boot for the version it finds.
game_build() {
  local build="$1" out="$2" lang extra="${VASM_EXTRA:-}"
  for lang in 0 1 2; do
    mkdir -p "$out/lang$lang"
    VASM_EXTRA="$extra -DLOV_LANG=$lang -DLOV_PASS1=1" vasm_build "$build" "$out/lang$lang"
  done
  python3 "$GAME_ROOT/tools/fixups.py" "$out/lang0/$VARIANT.Slave" "$out/lang1/$VARIANT.Slave" \
    "$out/lang2/$VARIANT.Slave" "$out/lov_fixups.s" > /dev/null
  VASM_EXTRA="$extra -I$out" vasm_build "$build" "$out"
  python3 "$GAME_ROOT/tools/fixups.py" --same "$out/lang0/$VARIANT.Slave" "$out/$VARIANT.Slave"
}

# TAPE=file installs a VERIFY slave input tape (tools/tape.py) as data/lovtape; the slave
# reads it with WHD_ARGS=CUSTOM5=1.
game_drives() {
  [ -n "${TAPE:-}" ] || return 0
  local tape
  tape="$(caller_path "$TAPE")"
  [ -f "$tape" ] || die "no tape $tape"
  cp -f "$tape" "$2/data/lovtape"
}

# The installer archive: tools/release.py replaces only the Slave, ReadMe and game icon
# records of the original and copies every other record byte for byte. FORCE=1 replaces an
# existing archive.
game_dist() {
  local force=
  [ "${FORCE:-0}" != 1 ] || force=--force
  (cd "$GAME_ROOT" && python3 tools/release.py --dist "$1" $force)
}

# The offline checks: every route tape builds, and, with the game installed, the one-degree
# ray-table model reproduces the game's own tables; with the German and French games
# installed too, src/offsets.s is current and every signature holds in all three versions.
game_check() {
  (
    cd "$GAME_ROOT"
    mkdir -p tmp/tapes
    for tape in tools/tapes/*.txt; do
      python3 tools/tape.py "$tape" "tmp/tapes/$(basename "$tape" .txt).tape" > /dev/null ||
        die "tape $tape does not build"
    done
    echo "$GAME: every tools/tapes route builds"
    if [ -d tmp/game/LegendsOfValour/data ]; then
      python3 tools/turning_tables.py > /dev/null || die "tools/turning_tables.py failed"
      echo "$GAME: tools/turning_tables.py matches the game's ray tables"
    else
      echo "$GAME: no tmp/game/LegendsOfValour (make unpack); ray-table check skipped"
    fi
    if python3 -c 'import sys; sys.path.insert(0, "tools"); import versions; sys.exit(not versions.available())'; then
      python3 tools/versions.py check || die "tools/versions.py check failed"
    else
      echo "$GAME: no German and French games (make unpack); version check skipped"
    fi
  )
}
