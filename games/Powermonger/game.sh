# games/Powermonger/game.sh: hooks for what game.conf cannot express.

# game_unpack: install tmp/game/Powermonger as Wepl's DIC install does. The install
# package holds the slave and the docs; the disk image comes from the IPF, decoded with the
# SPS capsimg library ($CAPSIMG) by tools/ipf2adf.py into Disk.1.
CAPSIMG="${CAPSIMG:-$AMIGA_SHARE/capsimg/capsimg.so}"

game_unpack() {
  local dest="tmp/game/Powermonger" stage pkg
  if [ -e "$dest" ]; then
    if [ "${FORCE:-0}" = 1 ]; then rm -rf "$dest"; else
      echo "kept the existing $dest (FORCE=1 replaces it)"; return 0
    fi
  fi
  [ -f "$CAPSIMG" ] || die "no capsimg library at $CAPSIMG (set CAPSIMG)"
  stage="$(mktemp -d "$GAME_ROOT/tmp/unpack.XXXXXX")"
  "$LHA" "xqw=$stage" "tmp/archives/Powermonger.lha"
  pkg="$stage/Powermonger Install"
  mkdir -p "$stage/Powermonger/save"		# the install script makes it; saved games go there
  cp "$pkg/Powermonger.Slave" "$pkg/ReadMe" "$pkg/Manual" "$pkg/Tips" "$stage/Powermonger/"
  cp "$pkg/Powermonger.newexot" "$stage/Powermonger/Powermonger.info"
  python3 -I tools/ipf2adf.py "$CAPSIMG" tmp/archives/PowerMonger.ipf "$stage/Powermonger/Disk.1"
  mkdir -p tmp/game
  mv "$stage/Powermonger" "$dest"
  rm -rf "$stage"
  echo "unpacked $dest"
}
