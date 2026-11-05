#!/usr/bin/env bash
# Build and play the experimental fixed-rate conversion with normal input and sound
# (make play60). The CPU selects the variant: Stellar7-Sim68000 on 68000/68010,
# Stellar7-Sim60 on 68020 and later. A named SETUP decides the CPU before the selection.
# Every common/run.sh option applies; WHD_ARGS defaults to CUSTOM1=1.
set -euo pipefail
COMMON="${COMMON:-$(cd "$(dirname "$0")/../../../common" && pwd)}"
. "$COMMON/env.sh"
setup="${AMIGA_SETUP:-${SETUP:-}}"
[ "$setup" != custom ] || setup=""
# In a subshell: the selection must not leave the shared launcher's state behind.
cpu="$(AMIGA_SETUP="$setup" bash -c '. "$FSUAE_COMMON"; fsuae_setup >&2 && echo "${CPU:-68000}"')"
case "$cpu" in
  68000|68010) VARIANT=Stellar7-Sim68000 ;;
  68020|68EC020|68030|68EC030|68040*|68EC040*|68060*|68EC060*) VARIANT=Stellar7-Sim60 ;;
  *) echo "Unsupported CPU for fixed-rate selection: $cpu" >&2; exit 1 ;;
esac
export VARIANT
export WHD_ARGS="${WHD_ARGS:-CUSTOM1=1}"
exec "$COMMON/run.sh"
