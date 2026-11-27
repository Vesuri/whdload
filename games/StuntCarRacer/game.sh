# Stunt Car Racer: build hook (common/template/game.sh lists the hooks).

# The slave includes the Unleashed blob (src/unleashed.s), which tools/ulblob.py assembles
# twice into the ignored tmp/include/ (INCLUDES in game.conf) to find its relocations. Its
# sources join the slave's in the .deps the release packages.
game_build() {
  python3 -I tools/ulblob.py "$GAME_ROOT/tmp/include" > /dev/null ||
    die "tools/ulblob.py failed"
  vasm_build "$1" "$2"
  printf '%s\n' src/unleashed.s src/unleashed_syms.i >> "$2/$VARIANT.deps"
}
