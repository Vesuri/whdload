#!/usr/bin/env bash
# Publish a game's release on GitHub (docs/releasing.md, "Publishing").
#   common/release.sh               (make release: a dry run that shows what would happen)
#   PUBLISH=1 common/release.sh     (make release PUBLISH=1: publish it)
#   REPLACE=1                       also delete the game's earlier releases and their tags
#   NOTES=file                      the release notes, when the ReadMe entry is not a list
# It builds the archive with make dist at HEAD, then common/tools/publish_release.py tags
# HEAD, creates the release with the archive and its .sha256, checks the download and
# lists the release in the root README.md.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
load_game
cd "$REPO"

[ -z "$(git status --porcelain -- "games/$GAME" common)" ] ||
  die "games/$GAME or common/ has uncommitted changes; release from a clean commit"
FORCE=1 "$COMMON/dist.sh"

first="${VARIANTS%% *}"
TITLE="$TITLE" AUTHOR="$AUTHOR" exec python3 "$COMMON/tools/publish_release.py" \
  --game "$GAME" --slave "$GAME_ROOT/tmp/build/release/$first.Slave" --dist "$REPO/dist"
