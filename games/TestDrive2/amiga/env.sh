#!/usr/bin/env bash
# Source this for the shared Amiga environment that AmigaXDev installs (~/.local/share/amiga):
# Kickstarts, Workbench, WHDLoad, the toolchain and PATH.  Every variable can be overridden from
# the environment; the tools take the same defaults from AmigaXDev's amigaxdev.env.
. "${AMIGA_ENV:-$HOME/.local/share/amiga/env.sh}"
