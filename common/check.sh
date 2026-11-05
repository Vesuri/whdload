#!/usr/bin/env bash
# Checks before a commit.
#   common/check.sh repo     the whole tree: no local paths, no work identities, no
#                            copyrighted or built files tracked or about to be
#   common/check.sh game     one game (GAME or the current directory): its release build
#                            still gives the bytes in release/slaves.sha256, then game_check
#   common/check.sh record   write release/slaves.sha256 from the current release build
# A shared change (common/, docs/) must leave every game's slaves.sha256 matching.
set -euo pipefail
. "$(dirname "$0")/lib.sh"

case "${1:-}" in
  repo)
    cd "$REPO"
    status=0
    # Tracked files and new files that are not ignored.
    list() { git ls-files -co --exclude-standard -- . ':!common/check.sh'; }
    hits="$(list | tr '\n' '\0' | xargs -0 grep -nIE \
      '/Users/|/home/[a-z]|~/Documents|~/Projects|RetroPie|amiberry|(^|[^A-Za-z0-9_.>/-])/tmp/' 2>/dev/null || true)"
    if [ -n "$hits" ]; then echo "local paths:"; echo "$hits"; status=1; fi
    hits="$(list | tr '\n' '\0' | xargs -0 grep -nIiE 'datadog|ddog' 2>/dev/null || true)"
    if [ -n "$hits" ]; then echo "work-related content:"; echo "$hits"; status=1; fi
    hits="$(list | grep -iE '\.(slave|lha|lzh|lzx|adf|dms|rom|bin|rec|uss|png|zip|rtb)$|(^|/)kick[0-9]+\.a[0-9]+' || true)"
    if [ -n "$hits" ]; then echo "copyrighted or built files:"; echo "$hits"; status=1; fi
    if [ "$status" = 0 ]; then echo "repo: clean"; fi
    exit "$status"
    ;;
  game|record)
    load_game
    cd "$GAME_ROOT"
    sums=release/slaves.sha256
    for v in $VARIANTS; do
      env -u GAME_DIR -u SLAVE_FILE -u SOURCE VARIANT="$v" "$COMMON/build.sh" release > /dev/null
    done
    if [ "$1" = record ]; then
      (cd tmp/build/release && for v in $VARIANTS; do shasum -a 256 "$v.Slave"; done) > "$sums"
      echo "recorded games/$GAME/$sums"
      exit 0
    fi
    if [ -f "$sums" ]; then
      (cd tmp/build/release && shasum -a 256 -c --quiet "$GAME_ROOT/$sums") ||
        die "the release build differs from $sums (make record if that is intended)"
      echo "$GAME: release build matches $sums"
    else
      echo "$GAME: no $sums (make record writes it)"
    fi
    hook game_check
    ;;
  *) die "usage: check.sh repo|game|record" ;;
esac
