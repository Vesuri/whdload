#!/usr/bin/env bash
# Start a game from common/template: common/new.sh <Game> (make new GAME=<Game>).
# <Game> is the directory name: letters and digits, usually the slave's base name.
set -euo pipefail
COMMON="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$COMMON")"
game="${1:-}"
case "$game" in ''|*[!A-Za-z0-9]*) echo "usage: new.sh <Game> (letters and digits)" >&2; exit 1 ;; esac
dest="$REPO/games/$game"
[ ! -e "$dest" ] || { echo "games/$game exists" >&2; exit 1; }
mkdir -p "$REPO/games"
cp -R "$COMMON/template" "$dest"
for f in game.conf AGENTS.md release/release.json; do
  sed -e "s/@GAME@/$game/g" -e "s/@TITLE@/$game/g" "$dest/$f" > "$dest/$f.new" && mv "$dest/$f.new" "$dest/$f"
done
echo "games/$game: fill in game.conf (TITLE, AUTHOR, UPSTREAM, VARIANTS, KICKS, SETUP),"
echo "AGENTS.md (@SCOPE@, @AUTHOR@), inputs.sha256 and release/release.json"
