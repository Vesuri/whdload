#!/usr/bin/env bash
# Play a build on an A1200/040 with arcade handling and arcade race timing, on the native
# arm64 FS-UAE, and stay until it exits (make aja). The release build by default;
# SLAVE=tmp/build/NAME.slave plays another (the r39 handling candidate was played this way).
# Every common/run.sh option applies.
set -euo pipefail
COMMON="${COMMON:-$(cd "$(dirname "$0")/../../../common" && pwd)}"
export SETUP="${SETUP:-a1200-040}"
# FSUAE_ARM from the shared environment, read in a subshell: exporting the whole shared
# environment here would override game.conf's values (NDK) in the build.
export FSUAE="${FSUAE:-$(. "$COMMON/env.sh" > /dev/null 2>&1; printf '%s' "$FSUAE_ARM")}"
export WHD_ARGS="${WHD_ARGS:-CUSTOM1=2 CUSTOM5=2 CACHE PRELOAD}"
export WAIT="${WAIT:-1}"
exec "$COMMON/run.sh"
