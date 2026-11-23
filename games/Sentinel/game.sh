# Sentinel: game.sh hooks (common/template/game.sh describes them).

# make check: EdgeStep against the game's edge scan converter (tools/edgecheck.py) and
# SpanFill against its span filler (tools/spancheck.py).
game_check() {
  python3 tools/edgecheck.py 20000 && python3 tools/spancheck.py 30000
}
