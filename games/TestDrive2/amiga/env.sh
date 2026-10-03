#!/usr/bin/env bash
# Source this to put the shared /path/to/.local Amiga toolchain on PATH.
TC="/path/to/.local"
export PATH="$TC/opt/bin:$TC:$TC/fs-uae:$PATH"
export KICKSTART="${KICKSTART:-/path/to/kickstarts/kick31.rom}"
