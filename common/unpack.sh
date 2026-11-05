#!/usr/bin/env bash
# Verify a game's original archives and unpack them into tmp/game/.
#   ARCHIVES=<directory> common/unpack.sh     (make unpack ARCHIVES=<directory>)
# inputs.sha256 in the game directory pins every input, in `shasum -a 256` format
# ("<sha256>  <file name>"). Each named file is taken from tmp/archives/ or, when it is not
# there yet, copied from $ARCHIVES (searched recursively; of several files with that name,
# the first whose hash matches), then checked against its hash.
# Archives (.lha, .lzh, .zip, .lzx) are then unpacked into tmp/game/. A drawer already in
# tmp/game/ is kept unless FORCE=1. Other files (disk images, ...) are only verified.
# A game whose data needs more than unpacking (an installer, disk images) defines
# game_unpack in game.sh; it runs after the verification, in the game directory.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
load_game
cd "$GAME_ROOT"

[ -f inputs.sha256 ] || die "no inputs.sha256 in games/$GAME"
mkdir -p tmp/archives tmp/game

names=()
while read -r sum name; do
  case "$sum" in ''|'#'*) continue ;; esac
  names+=("$name")
  if [ ! -f "tmp/archives/$name" ]; then
    [ -n "${ARCHIVES:-}" ] || die "tmp/archives/$name is missing: pass ARCHIVES=<directory holding it>"
    src="" found=0
    while IFS= read -r f; do
      found=1
      if [ "$(shasum -a 256 "$f" | cut -d' ' -f1)" = "$sum" ]; then src="$f"; break; fi
    done < <(find "$(caller_path "$ARCHIVES")" -type f -name "$name" -print 2>/dev/null)
    [ "$found" = 1 ] || die "no $name under $ARCHIVES"
    [ -n "$src" ] || die "no $name under $ARCHIVES matches inputs.sha256"
    cp "$src" "tmp/archives/$name"
  fi
done < inputs.sha256
(cd tmp/archives && grep -vE '^[[:space:]]*(#|$)' ../../inputs.sha256 | shasum -a 256 -c --quiet -) ||
  die "an input differs from inputs.sha256"
echo "inputs verified: ${names[*]}"

if has_hook game_unpack; then
  game_unpack
  exit 0
fi

for name in "${names[@]}"; do
  stage="$(mktemp -d "$GAME_ROOT/tmp/unpack.XXXXXX")"
  case "$name" in
    *.lha|*.LHA|*.lzh|*.LZH) "$LHA" "xqw=$stage" "tmp/archives/$name" ;;
    *.zip|*.ZIP) unzip -q "tmp/archives/$name" -d "$stage" ;;
    *.lzx|*.LZX) command -v unar > /dev/null || die "unar is needed for $name"
                 unar -q -o "$stage" "tmp/archives/$name" ;;
    *) rmdir "$stage"; continue ;;
  esac
  for entry in "$stage"/* "$stage"/.[!.]*; do
    [ -e "$entry" ] || continue
    target="tmp/game/$(basename "$entry")"
    if [ -e "$target" ]; then
      if [ "${FORCE:-0}" = 1 ]; then rm -rf "$target"; else
        echo "kept the existing $target (FORCE=1 replaces it)"; continue
      fi
    fi
    mv "$entry" "$target"
    echo "unpacked $target"
  done
  rm -rf "$stage"
done
