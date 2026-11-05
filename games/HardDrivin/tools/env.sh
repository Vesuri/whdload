#!/usr/bin/env bash
# The harness environment: the shared one (common/env.sh) with the NDK 3.2 includes the
# slave is built against (game.conf's NDK). Source it from the game directory before
# running a tool that assembles or boots by itself:  . tools/env.sh
export NDK="${NDK:-${AMIGA_SHARE:-$HOME/.local/share/amiga}/ndk/Include_I}"
# shellcheck disable=SC1091
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../common" && pwd)/env.sh"
