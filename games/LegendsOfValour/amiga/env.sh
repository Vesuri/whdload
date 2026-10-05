#!/usr/bin/env bash
# Source this to put the shared ~/.local Amiga toolchain on PATH.
TC="$HOME/.local"
export PATH="$TC/opt/bin:$TC:$TC/fs-uae:$PATH"
export KICKSTART="${KICKSTART:-$AMIGA_SHARE/Kickstarts/kick31.rom}"
