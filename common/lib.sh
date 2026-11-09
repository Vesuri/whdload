#!/usr/bin/env bash
# Shared by common/*.sh: find the game, load its configuration and the shared environment.
# Sourced, never run. Works with macOS /bin/bash 3.2.
#
# The game is $GAME (a directory name under games/) or, when that is unset, the games/<Game>
# directory that contains the current directory. common/try.sh instead sets TRY_ROOT, a
# directory under try/tmp/ with a generated game.conf, and GAME. load_game then sets:
#   REPO        the repository root
#   GAME        the game's directory name
#   GAME_ROOT   games/<Game>, absolute
#   VARIANT     the selected slave (default: the first of VARIANTS)
# and every game.conf value, with these defaults filled in:
#   GAME_DIR    $VARIANT          installed game drawer under tmp/game/
#   SLAVE_FILE  $VARIANT.Slave    slave file name in that drawer
#   SOURCE      src/$VARIANT.s    main slave source
#
# Precedence: the caller's environment (make command-line variables included) beats
# game.conf, which beats the shared env.sh defaults.

COMMON="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$COMMON")"

die() { echo "${0##*/}: $*" >&2; exit 1; }

# The game's directory name, from $GAME or the current directory.
find_game() {
  if [ -n "${GAME:-}" ]; then
    case "$GAME" in */*|.*|'') die "GAME must be a directory name under games/" ;; esac
    [ -f "$REPO/games/$GAME/game.conf" ] || die "no games/$GAME/game.conf (make list shows the games)"
    return 0
  fi
  local dir="$PWD"
  while [ "$dir" != / ] && [ "$dir" != "$REPO" ]; do
    if [ "$(dirname "$dir")" = "$REPO/games" ] && [ -f "$dir/game.conf" ]; then
      GAME="$(basename "$dir")"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  die "run this inside games/<Game> or set GAME=<Game> (make list shows the games)"
}

# The caller's exported environment, captured before anything else is loaded, so it can be
# reapplied on top of game.conf.
USER_ENV="$(export -p | sed 's/^declare -x /export /' |
  grep -vE '^export (BASHOPTS|SHELLOPTS|BASH_[A-Za-z_]*|_|PWD|OLDPWD|SHLVL)(=|$)')"

# Was VAR in the caller's environment?
user_set() { printf '%s\n' "$USER_ENV" | grep -qE "^export $1(=|\$)"; }

_source_conf() {
  # shellcheck disable=SC1091
  . "$GAME_ROOT/game.conf"
  eval "$USER_ENV"
}

load_game() {
  if [ -n "${TRY_ROOT:-}" ]; then
    [ -f "$TRY_ROOT/game.conf" ] || die "no $TRY_ROOT/game.conf"
    GAME="${GAME:-$(basename "$TRY_ROOT")}"
    GAME_ROOT="$TRY_ROOT"
  else
    find_game
    GAME_ROOT="$REPO/games/$GAME"
  fi
  export GAME GAME_ROOT REPO COMMON
  # First pass for VARIANTS; the second sees $VARIANT, so game.conf can depend on it.
  VARIANT="${VARIANT:-}"
  _source_conf
  [ -n "${VARIANTS:-}" ] || die "games/$GAME/game.conf sets no VARIANTS"
  if [ -z "$VARIANT" ]; then
    set -- $VARIANTS
    VARIANT="$1"
  fi
  case " $VARIANTS " in *" $VARIANT "*) ;; *) die "VARIANT must be one of: $VARIANTS" ;; esac
  _source_conf
  GAME_DIR="${GAME_DIR:-$VARIANT}"
  SLAVE_FILE="${SLAVE_FILE:-$VARIANT.Slave}"
  SOURCE="${SOURCE:-src/$VARIANT.s}"
  export VARIANT GAME_DIR SLAVE_FILE SOURCE
  # shellcheck disable=SC1091
  . "$COMMON/env.sh"
  if [ -f "$GAME_ROOT/game.sh" ]; then
    # shellcheck disable=SC1091
    . "$GAME_ROOT/game.sh"
  fi
}

# Call a game.sh hook if the game defines it.
hook() {
  local name="$1"; shift
  if declare -F "$name" > /dev/null; then "$name" "$@"; else return 0; fi
}
has_hook() { declare -F "$1" > /dev/null; }

# An absolute path for a path given relative to the caller's directory. make passes
# CALLER_DIR when it changes into the game directory.
caller_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s/%s\n' "${CALLER_DIR:-$PWD}" "$1" ;;
  esac
}
