# Grand Prix Circuit hooks (common/template/game.sh lists them).

# Each archive is unpacked into a drawer named after it: tmp/game/GrandPrixCircuit_v1.0_0008
# is the installed v1.0 game that runs (its GrandPrixCircuit drawer), tmp/game/GrandPrixCircuit
# the installer package. tools/check_inputs.py then checks every installed file against
# manifest/GrandPrixCircuit_v1.0_0008.files.json.
game_unpack() {
  local sum name base stage
  while read -r sum name; do
    case "$sum" in ''|'#'*) continue ;; esac
    case "$name" in *.lha) ;; *) continue ;; esac
    base="${name%.lha}"
    if [ -e "tmp/game/$base" ]; then
      if [ "${FORCE:-0}" = 1 ]; then rm -rf "tmp/game/$base"; else
        echo "kept the existing tmp/game/$base (FORCE=1 replaces it)"; continue
      fi
    fi
    stage="$(mktemp -d "$GAME_ROOT/tmp/unpack.XXXXXX")"
    "$LHA" "xqw=$stage" "tmp/archives/$name"
    mv "$stage" "tmp/game/$base"
    echo "unpacked tmp/game/$base"
  done < inputs.sha256
  python3 tools/check_inputs.py
}

# The VERIFY build must still assemble, and the installed game must match its manifest once
# make unpack has installed it. The capture and emulator-driven checks are run by hand
# (docs/development.md).
game_check() {
  (
    cd "$GAME_ROOT"
    "$COMMON/build.sh" verify > /dev/null
    echo "verify: builds"
    if [ -d tmp/game/GrandPrixCircuit_v1.0_0008 ]; then
      python3 tools/check_inputs.py
    else
      echo "skipped (no installed game; make unpack): tools/check_inputs.py"
    fi
  )
}
