# Stellar 7 hooks (common/template/game.sh lists them).

# The experimental installer snapshot: tools/package_release.py edits the original
# installer to offer the three builds.
game_dist() {
  python3 "$GAME_ROOT/tools/package_release.py" --dist "$1"
}

# The quick unit tests; the emulator-driven checks are run by hand (docs/development.md).
game_check() {
  (cd "$GAME_ROOT" && python3 -m unittest discover -s tools -p 'test_*.py' -q)
}
