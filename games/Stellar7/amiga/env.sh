#!/usr/bin/env bash
# Source this for the shared Amiga environment that AmigaXDev installs (~/.local/share/amiga):
# Kickstarts, Workbench, WHDLoad, the toolchain and PATH.  Every variable can be overridden from
# the environment; AmigaXDev's docs/environment.md describes them.  FSUAE: the x86_64 FS-UAE
# with the Barto gdb stub.
export FSUAE="${FSUAE:-$HOME/.local/fs-uae/fs-uae}"
. "${AMIGA_ENV:-$HOME/.local/share/amiga/env.sh}"
