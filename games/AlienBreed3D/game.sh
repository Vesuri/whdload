# Alien Breed 3D hooks (common/template/game.sh lists them).

# BUILD=original (-DORIGINAL) must rebuild Psygore's two slaves byte for byte; the release
# build adds Enhanced resolution (CUSTOM5).
game_check() {
  (cd "$GAME_ROOT" || exit 1
    for v in $VARIANTS; do
      env -u GAME_DIR -u SLAVE_FILE -u SOURCE VARIANT="$v" "$COMMON/build.sh" original > /dev/null &&
        cmp "tmp/build/original/$v.Slave" "tmp/game/AlienBreed3DHD/$v.slave" || exit 1
    done) && echo "original: both slaves identical to Psygore's"
}
