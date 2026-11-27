# Stunt Track Racer: build hook (common/template/game.sh lists the hooks).

# The enhanced framerate is Stunt Car Racer's: its relocation table (src/relocs.s) and its
# Unleashed blob (src/unleashed.s), which that game's tools/ulblob.py assembles here for
# NTSC into the ignored tmp/include/ (INCLUDES in game.conf). The two main programs have the
# same layout (docs/development.md).
game_build() {
  python3 -I ../StuntCarRacer/tools/ulblob.py "$GAME_ROOT/tmp/include" --define NTSC=1 \
    > /dev/null || die "../StuntCarRacer/tools/ulblob.py failed"
  vasm_build "$1" "$2"
}
