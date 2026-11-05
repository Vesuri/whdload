#!/usr/bin/env bash
# Build a game's release slaves and repack its original archives into dist/.
#   common/dist.sh            (make dist; FORCE=1 replaces an existing archive)
# release/release.json describes the archives (common/tools/package_release.py). A game that
# needs more (changed icons, a rewritten installer) defines game_dist DIST in game.sh, which
# runs after the release build instead of the generic packager.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
load_game
cd "$GAME_ROOT"
DIST="$REPO/dist"

for v in $VARIANTS; do
  env -u GAME_DIR -u SLAVE_FILE -u SOURCE VARIANT="$v" "$COMMON/build.sh" release
done

if has_hook game_dist; then
  game_dist "$DIST"
  exit 0
fi
[ -f release/release.json ] || die "no release/release.json in games/$GAME"
slaves=()
for v in $VARIANTS; do
  slaves+=(--slave "$(env -u GAME_DIR -u SLAVE_FILE -u SOURCE VARIANT="$v" bash -c \
    '. "$1/lib.sh"; load_game; printf "%s=%s\n" "$VARIANT" "$GAME_ROOT/tmp/build/release/$SLAVE_FILE"' _ "$COMMON")")
done
force=()
[ "${FORCE:-0}" != 1 ] || force=(--force)
python3 "$COMMON/tools/package_release.py" --game-root "$GAME_ROOT" --dist "$DIST" \
  "${slaves[@]}" ${force[@]+"${force[@]}"}
