# Legends of Valour hooks (common/template/game.sh lists them).

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
# ray-table model reproduces the game's own tables.
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
  )
}
