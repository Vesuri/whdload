# Sentinel: game.sh hooks (common/template/game.sh describes them).

# make check: EdgeStep against the game's edge scan converter (tools/edgecheck.py).
game_check() {
  python3 tools/edgecheck.py 20000
}
