# Red Baron hooks (common/template/game.sh lists them).

# The host unit tests in tools/test_*.py (models, generated VERIFY cases, capture readers on
# synthetic data): none needs the game, a build or a capture. The emulator-driven checks
# are run by hand (docs/development.md).
game_check() {
  (
    cd "$GAME_ROOT"
    log=tmp/check-unittest.log
    mkdir -p tmp
    python3 -B -m unittest discover -q -s tools -p 'test_*.py' > "$log" 2>&1 ||
      { tail -40 "$log" >&2; die "tools/test_*.py failed ($log)"; }
    echo "passed: tools/test_*.py ($(grep -o 'Ran [0-9]* tests' "$log"))"
  )
}
