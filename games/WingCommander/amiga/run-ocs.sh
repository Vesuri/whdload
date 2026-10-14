#!/usr/bin/env bash
# OCS entry point; share drive preparation and process ownership with run.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export WC_VARIANT=ocs
export AMIGA_SETUP="${AMIGA_SETUP:-a3000}"
export FSUAE_RUN="${FSUAE_RUN:-../tmp/run-ocs}"
# An explicitly empty WHD_ARGS selects original behaviour.
export WHD_ARGS="${WHD_ARGS-CUSTOM5=1 DCACHE}"

if [ "${1:-}" != stop ] && [ -z "${SLAVE:-}" ]; then
  . "$ROOT/amiga/env.sh"
  mkdir -p "$ROOT/tmp"
  build_root=$(mktemp -d "$ROOT/tmp/ocs-launch.XXXXXX")
  (
    cd "$ROOT"
    python3 tools/ocs_memory_build.py --public --output "$build_root/build"
  )
  export SLAVE="$build_root/build/WingCommander.Slave"
fi

exec /bin/bash "$ROOT/amiga/run.sh" "$@"
