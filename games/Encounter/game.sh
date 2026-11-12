# Encounter hooks (common/template/game.sh lists them).

# The verify build also traps execution of the chip program's code: tools/relocs.py writes
# the reached instructions of the installed disk.1 to tmp/build/verify/codebits.i (derived
# from the game, never tracked), which src/EncounterHD.s includes under VERIFY.
game_build() {
  local BUILD="$1" OUT="$2"
  if [ "$BUILD" = verify ]; then
    python3 tools/relocs.py --codebits "$OUT/codebits.i" >/dev/null ||
      die "tools/relocs.py --codebits failed"
    INCLUDES="${INCLUDES:-} ${OUT#"$GAME_ROOT"/}"
  fi
  vasm_build "$BUILD" "$OUT"
}
