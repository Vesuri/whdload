# Indianapolis 500 hooks (common/template/game.sh lists them).

# The installed release: tools/package_release.py replaces the slave and the ReadMe in the
# SPS 0686 installed archive and copies every other member's bytes unchanged.
game_dist() {
  local force=()
  [ "${FORCE:-0}" != 1 ] || force=(--force)
  python3 "$GAME_ROOT/tools/package_release.py" --dist "$1" ${force[@]+"${force[@]}"}
}
