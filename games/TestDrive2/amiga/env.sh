#!/usr/bin/env bash
# Source this for the shared Amiga files (~/.local/share/amiga) and toolchain (~/.local).
# Every path can be overridden from the environment; tools/local_env.py has the same defaults.
SHARED="$HOME/.local/share/amiga"
export KICKSTART="${KICKSTART:-$SHARED/Kickstarts/kick40063.A600}"              # host: KS 3.1
export KICKSTART_A1200="${KICKSTART_A1200:-$SHARED/Kickstarts/kick40068.A1200}"  # A1200 host
export KICKSTART13="${KICKSTART13:-$SHARED/Kickstarts/kick34005.A500}"          # slave's KickEmu
export RTB="${RTB:-$SHARED/Kickstarts/kick34005.A500.RTB}"
export WORKBENCH_ADF="${WORKBENCH_ADF:-$SHARED/Workbenchv2.04rev37.67Workbench.adf}"
export WHDLOAD_BINARY="${WHDLOAD_BINARY:-$SHARED/WHDLoad-20.0/C/WHDLoad}"
export FSUAE_COMMON="${FSUAE_COMMON:-$SHARED/fsuae_common.sh}"
export LHA="${LHA:-$SHARED/lha-compressor/src/lha}"
export AMIGA_TOOLCHAIN="${AMIGA_TOOLCHAIN:-$HOME/.local/opt}"
export VASM="${VASM:-$HOME/.local/vasmm68k_mot}"
export PATH="$AMIGA_TOOLCHAIN/bin:$HOME/.local:$HOME/.local/fs-uae:$PATH"
unset SHARED
