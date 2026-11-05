#!/usr/bin/env bash
# The shared environment from AmigaXDev's `make setup`. Every value already set is kept, so
# the caller's environment and game.conf beat the shared defaults.
# shellcheck disable=SC1091
. "${AMIGA_ENV:-$HOME/.local/share/amiga/env.sh}"
