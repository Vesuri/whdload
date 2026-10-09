#!/usr/bin/env bash
# Source this to put the shared ~/.local Amiga toolchain on PATH.
TC="$HOME/.local"
export PATH="$TC/opt/bin:$TC:$TC/fs-uae:$PATH"
# Shared Amiga files, each overridable from the environment:
#   KICKSTART      Kickstart 3.1 (A600 ROM); A1200 runs pass Kickstarts/kick40068.A1200
#   WHDLOAD        WHDLoad 20.0 directory (Include/ for the makefile); the plain WHDLoad/ there is 19.2
#   WHDLOAD_BINARY the WHDLoad binary run.sh copies (default $WHDLOAD/C/WHDLoad)
#   WORKBENCH_ADF  Workbench 2.04 floppy, inserted only with WB=1
AMIGA_SHARE="$HOME/.local/share/amiga"
export KICKSTART="${KICKSTART:-$AMIGA_SHARE/Kickstarts/kick40063.A600}"
export WHDLOAD="${WHDLOAD:-$AMIGA_SHARE/WHDLoad-20.0}"
export WHDLOAD_BINARY="${WHDLOAD_BINARY:-$WHDLOAD/C/WHDLoad}"
export WORKBENCH_ADF="${WORKBENCH_ADF:-$AMIGA_SHARE/Workbenchv2.04rev37.67Workbench.adf}"

export KICK13="${KICK13:-$AMIGA_SHARE/Kickstarts/kick34005.A500}"
export RTB="${RTB:-$AMIGA_SHARE/Kickstarts/kick34005.A500.RTB}"
export KICKSTART_A1200="${KICKSTART_A1200:-$AMIGA_SHARE/Kickstarts/kick40068.A1200}"
