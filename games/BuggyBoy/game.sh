# Buggy Boy: build hook (common/template/game.sh lists the hooks).

# The shipped 1.3 was assembled against a keyboard.s that reads _resload PC-relative.
# WHDLoad 20.1's keyboard.s reads it absolute (its 21.03.12 history entry), which gives
# the slave a relocation hunk that WHDLoad refuses ("Slave is illegal, contains
# relocations"). Assemble against a copy of the installed 20.1 file, generated into the
# ignored tmp/include/whdload/ (INCLUDES in game.conf, searched before $WHDLOAD/Src/sources),
# with ",pc" added to its two _resload operands. Nothing of WHDLoad is tracked.
game_build() {
  local src="$WHDLOAD/Src/sources/whdload/keyboard.s" dst="$GAME_ROOT/tmp/include/whdload/keyboard.s"
  mkdir -p "${dst%/*}"
  LC_ALL=C sed 's/(_resload),/(_resload,pc),/' "$src" > "$dst.tmp"
  [ "$(LC_ALL=C grep -c '(_resload,pc),' "$dst.tmp")" = 2 ] ||
    die "$src: expected two absolute (_resload) operands"
  mv "$dst.tmp" "$dst"
  vasm_build "$1" "$2"
}
