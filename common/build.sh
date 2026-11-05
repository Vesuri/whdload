#!/usr/bin/env bash
# Build a game's slaves.
#   common/build.sh [BUILD]        BUILD: release (default), verify, developer or any name
#                                  the game defines; VARIANT=name builds only that slave
#   common/build.sh clean          remove tmp/build/
# Output: games/<Game>/tmp/build/<BUILD>/<SLAVE_FILE>, with its listing (.lst), the source
# files it was assembled from (.deps, one path per line, relative to the game).
#
# The default build assembles $SOURCE with vasm. game.conf adjusts it with
#   VASM_FLAGS       default -m68000 -x -devpac -Fhunkexe -nosym
#   INCLUDES         extra include directories, relative to the game (src/ is always first)
#   DEFINES          defines for every build, e.g. "-DFOO=1"
#   DEFINES_<BUILD>  defines for one build; the defaults are none for release,
#                    -DVERIFY=1 for verify and -DDEVELOPER=1 for developer
# A game with its own build defines game_build BUILD OUT in game.sh, which must leave
# OUT/$SLAVE_FILE for the selected VARIANT (and should write OUT/$VARIANT.deps).
set -euo pipefail
. "$(dirname "$0")/lib.sh"
load_game
cd "$GAME_ROOT"

BUILD="${1:-${BUILD:-release}}"
case "$BUILD" in
  clean) rm -rf tmp/build; exit 0 ;;
  *[!a-zA-Z0-9_-]*|'') die "BUILD must be a plain name" ;;
esac
OUT="$GAME_ROOT/tmp/build/$BUILD"
mkdir -p "$OUT"

build_one() {
  if has_hook game_build; then
    game_build "$BUILD" "$OUT"
  else
    local defines flags inc incs=() d
    case "$BUILD" in
      release) defines="${DEFINES_release-}" ;;
      verify) defines="${DEFINES_verify--DVERIFY=1}" ;;
      developer) defines="${DEFINES_developer--DDEVELOPER=1}" ;;
      *) eval "defines=\"\${DEFINES_$BUILD-}\"" ;;
    esac
    flags="${VASM_FLAGS:--m68000 -x -devpac -Fhunkexe -nosym}"
    [ -f "$SOURCE" ] || die "no $SOURCE (set SOURCE in game.conf)"
    incs=(-I"$GAME_ROOT/src")
    for inc in ${INCLUDES:-}; do incs+=(-I"$GAME_ROOT/$inc"); done
    incs+=(-I"$AMIGA_INCLUDE" -I"$WHDLOAD/Include" -I"$WHDLOAD/Src/sources" -I"$NDK")
    # shellcheck disable=SC2086  # flag lists are word-split on purpose
    "$VASM" $flags ${DEFINES:-} $defines "${incs[@]}" -quiet \
      -o "$OUT/$SLAVE_FILE" -L "$OUT/$VARIANT.lst" "$SOURCE"
    # The files the slave is made of, for the release archive's source (common/tools/
    # package_release.py). vasm lists every include it opened; keep the game's own.
    # shellcheck disable=SC2086
    "$VASM" $flags ${DEFINES:-} $defines "${incs[@]}" -quiet -depend=list \
      -o "$OUT/$SLAVE_FILE" "$SOURCE" |
      while IFS= read -r d; do
        case "$d" in "$GAME_ROOT"/*) d="${d#"$GAME_ROOT"/}" ;; /*) continue ;; esac
        [ -f "$d" ] && printf '%s\n' "$d"
      done | sort -u > "$OUT/$VARIANT.deps.tmp"
    { printf '%s\n' "$SOURCE"; cat "$OUT/$VARIANT.deps.tmp"; } | awk '!seen[$0]++' > "$OUT/$VARIANT.deps"
    rm -f "$OUT/$VARIANT.deps.tmp"
  fi
  [ -f "$OUT/$SLAVE_FILE" ] || die "the $BUILD build left no $OUT/$SLAVE_FILE"
  echo "$BUILD: tmp/build/$BUILD/$SLAVE_FILE"
}

# Each variant reloads game.conf with its own VARIANT, so build them one process each.
if user_set VARIANT; then
  build_one
else
  for v in $VARIANTS; do
    env -u GAME_DIR -u SLAVE_FILE -u SOURCE VARIANT="$v" "$0" "$BUILD"
  done
fi
