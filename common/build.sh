#!/usr/bin/env bash
# Build a game's slaves.
#   common/build.sh [BUILD]        BUILD: release (default), verify, developer or any name
#                                  the game defines; VARIANT=name builds only that slave
#   common/build.sh clean          remove tmp/build/
# Output: games/<Game>/tmp/build/<BUILD>/<Variant>.Slave, with its listing (.lst), vasm's
# messages (.log) and the source files it was assembled from (.deps, one path per line,
# relative to the game).
# The run copies it into the game drawer as SLAVE_FILE.
#
# The default build assembles $SOURCE with vasm. game.conf adjusts it with
#   VASM_FLAGS       default -m68000 -x -devpac -Fhunkexe -nosym
#   INCLUDES         extra include directories, relative to the game (src/ is always first)
#   DEFINES          defines for every build, e.g. "-DFOO=1"
#   DEFINES_<BUILD>  defines for one build; the defaults are none for release,
#                    -DVERIFY=1 for verify and -DDEVELOPER=1 for developer
# and the caller adds flags for one build with VASM_EXTRA (e.g. "-DFOO=2 -L tmp/x.lst").
# A game with its own build defines game_build BUILD OUT in game.sh, which must leave
# OUT/$VARIANT.Slave for the selected VARIANT (and should write OUT/$VARIANT.deps); one that
# only generates sources first ends with vasm_build "$BUILD" "$OUT", the default build.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
load_game
cd "$GAME_ROOT"

BUILD="${1:-${BUILD:-release}}"
case "$BUILD" in
  clean) rm -rf tmp/build; exit 0 ;;
  # Letters, digits and _ only: the name is part of the DEFINES_<BUILD> variable.
  *[!a-zA-Z0-9_]*|'') die "BUILD must be letters, digits and _" ;;
esac
OUT="$GAME_ROOT/tmp/build/$BUILD"
mkdir -p "$OUT"

# The default build: assemble $SOURCE with vasm into OUT. A game_build hook that only
# generates sources first calls it after them (vasm_build "$BUILD" "$OUT").
vasm_build() {
  local BUILD="$1" OUT="$2" defines flags inc incs=() d listing
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
  # The listing goes beside the slave unless the defines ask for one elsewhere (-L file).
  listing=(-L "$OUT/$VARIANT.lst")
  defines="$defines ${VASM_EXTRA:-}"
  case " ${DEFINES:-} $defines " in *" -L "*) listing=() ;; esac
  # shellcheck disable=SC2086  # flag lists are word-split on purpose
  # vasm's messages go to <Variant>.log, and to the terminal only when the build fails.
  if ! "$VASM" $flags ${DEFINES:-} $defines "${incs[@]}" -quiet \
      -o "$OUT/$VARIANT.Slave" ${listing[@]+"${listing[@]}"} "$SOURCE" > "$OUT/$VARIANT.log" 2>&1; then
    cat "$OUT/$VARIANT.log" >&2
    rm -f "$OUT/$VARIANT.Slave"
    die "the $BUILD build of $VARIANT failed (tmp/build/$BUILD/$VARIANT.log)"
  fi
  # The files the slave is made of, for the release archive's source (common/tools/
  # package_release.py). vasm lists every include it opened; keep the game's own.
  # shellcheck disable=SC2086
  "$VASM" $flags ${DEFINES:-} $defines "${incs[@]}" -quiet -depend=list \
    -o "$OUT/$VARIANT.Slave" "$SOURCE" 2>/dev/null |
    while IFS= read -r d; do
      case "$d" in "$GAME_ROOT"/*) d="${d#"$GAME_ROOT"/}" ;; /*) continue ;; esac
      [ -f "$d" ] && printf '%s\n' "$d"
    done | sort -u > "$OUT/$VARIANT.deps.tmp"
  { printf '%s\n' "$SOURCE"; cat "$OUT/$VARIANT.deps.tmp"; } | awk '!seen[$0]++' > "$OUT/$VARIANT.deps"
  rm -f "$OUT/$VARIANT.deps.tmp"
}

build_one() {
  if has_hook game_build; then
    game_build "$BUILD" "$OUT"
  else
    vasm_build "$BUILD" "$OUT"
  fi
  [ -f "$OUT/$VARIANT.Slave" ] || die "the $BUILD build left no $OUT/$VARIANT.Slave"
  echo "$BUILD: tmp/build/$BUILD/$VARIANT.Slave"
}

# Each variant reloads game.conf with its own VARIANT, so build them one process each.
if user_set VARIANT; then
  build_one
else
  for v in $VARIANTS; do
    env -u GAME_DIR -u SLAVE_FILE -u SOURCE VARIANT="$v" "$0" "$BUILD"
  done
fi
