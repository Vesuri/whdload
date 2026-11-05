# Hard Drivin' hooks (common/template/game.sh lists them).

# Both Amiga archives hold a HardDrivin drawer, so each is unpacked into a drawer named
# after it: tmp/game/HardDrivin_v3.0_0126/HardDrivin is the installed SPS 0126 game that
# runs, tmp/game/HardDrivin/HardDrivinInstall the installer package. harddriv.zip, the
# arcade ROM set the MAME tools read (tools/arcade/mame), stays packed in tmp/archives/.
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
}

# The comparison tools' failure-path unit tests. The rest of test_step1_tools needs the
# local step 1 captures, and the emulator-driven checks are run by hand (docs/development.md).
game_check() {
  (cd "$GAME_ROOT/tools" && python3 -m unittest -q test_step1_tools.ComparisonTests)
}
