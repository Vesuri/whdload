#!/usr/bin/env bash
# Source this to put the shared ~/.local Amiga toolchain on PATH and resolve the shared
# Amiga files.  Every default lives under ~/.local/share/amiga; override any of them in the
# environment:
#   KICKSTART        host ROM, Kickstart 3.1 A600 (boots Workbench, runs WHDLoad)
#   KICK13           Kickstart 1.3 that WHDLoad hands the kick13 slave (plus its .RTB)
#   KICKSTART_A1200  Kickstart 3.1 A1200, for the 68020 capture machine
#   WORKBENCH_ADF    Workbench 2.04 boot floppy
#   WHDLOAD_BINARY   the WHDLoad executable copied onto the game drive
TC="$HOME/.local"
AMIGA_SHARE="$TC/share/amiga"
export PATH="$TC/opt/bin:$TC:$TC/fs-uae:$PATH"
export KICKSTART="${KICKSTART:-$AMIGA_SHARE/Kickstarts/kick40063.A600}"
export KICK13="${KICK13:-$AMIGA_SHARE/Kickstarts/kick34005.A500}"
export KICKSTART_A1200="${KICKSTART_A1200:-$AMIGA_SHARE/Kickstarts/kick40068.A1200}"
export WORKBENCH_ADF="${WORKBENCH_ADF:-$AMIGA_SHARE/Workbenchv2.04rev37.67Workbench.adf}"
export WHDLOAD_BINARY="${WHDLOAD_BINARY:-$AMIGA_SHARE/WHDLoad/C/WHDLoad}"
for f in "$KICKSTART" "$KICK13" "$KICKSTART_A1200" "$WORKBENCH_ADF" "$WHDLOAD_BINARY"; do
  [ -f "$f" ] || echo "missing Amiga file: $f" >&2
done
