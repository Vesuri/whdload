#!/usr/bin/env bash
# Source this for the shared Amiga environment that AmigaXDev installs (~/.local/share/amiga):
# Kickstarts, Workbench, WHDLoad, the toolchain and PATH.  Every variable can be overridden from
# the environment; AmigaXDev's docs/environment.md describes them.  Project choices, set before
# the shared defaults:
#   WHDLOAD          WHDLoad 19.2 ($AMIGA_SHARE/WHDLoad): its headers build the slave and its
#                    C/WHDLoad (WHDLOAD_BINARY) runs on the game drive
#   VASM             the verified native build in tmp/vasm-native-src/vasm/ when present
_lov_root="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
export WHDLOAD="${WHDLOAD:-${AMIGA_SHARE:-$HOME/.local/share/amiga}/WHDLoad}"
if [ -z "${VASM:-}" ] && [ -x "$_lov_root/tmp/vasm-native-src/vasm/vasmm68k_mot" ]; then
  export VASM="$_lov_root/tmp/vasm-native-src/vasm/vasmm68k_mot"
fi
unset _lov_root
. "${AMIGA_ENV:-$HOME/.local/share/amiga/env.sh}"
