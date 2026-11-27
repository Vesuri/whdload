# Alien Breed 3D hooks (common/template/game.sh lists them).

# BUILD=original (-DORIGINAL) must rebuild Psygore's two slaves byte for byte; the release
# build adds Enhanced resolution (CUSTOM5).
game_check() {
  (cd "$GAME_ROOT" || exit 1
    for v in $VARIANTS; do
      env -u GAME_DIR -u SLAVE_FILE -u SOURCE VARIANT="$v" "$COMMON/build.sh" original > /dev/null &&
        cmp "tmp/build/original/$v.Slave" "tmp/game/AlienBreed3DHD/$v.slave" || exit 1
    done) && echo "original: both slaves identical to Psygore's" && game_check_cd32
}

# The CD32 version's Enhanced resolution is the $c4dc one's, mapped (tools/port.py): every
# site maps, the bytes each patch replaces are the same, and src/cd32.s and cd32segs.s are
# current. The two executables unpacked first when they are not.
game_check_cd32() {
  (cd "$GAME_ROOT" || exit 1
    [ -f tmp/exe/abd ] || python3 tools/exe.py > /dev/null || exit 1
    [ -f tmp/exe-cd32/abd ] || python3 tools/exe.py tmp/game/AlienBreed3DCD32/data/abd tmp/exe-cd32 > /dev/null || exit 1
    python3 tools/port.py check > tmp/port-check.txt || { grep -v ' code\| references' tmp/port-check.txt | tail -5; exit 1; }
  ) && echo "CD32: every site mapped, src/cd32.s and src/cd32segs.s current"
}
