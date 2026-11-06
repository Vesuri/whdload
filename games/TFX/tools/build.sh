#!/bin/bash
# The harness's build interface on common/build.sh: build TFX.Slave, fpsp040.Slave and
# fpsp060.Slave into tmp/build/release/ (CHIP_ONLY=1: the chiponly build into
# tmp/build/chiponly/). Extra arguments go to vasm for every variant (VASM_EXTRA, e.g.
# -L tmp/x.lst, which then applies to the TFX variant only); OUTPUT_SLAVE=path copies the
# TFX slave there as well.
set -euo pipefail
cd "$(dirname "$0")/.."
build=release
if [ "${CHIP_ONLY:-0}" = 1 ]; then build=chiponly; fi
unset CHIP_ONLY
if [ $# -gt 0 ]; then
  VASM_EXTRA="${VASM_EXTRA:-} $*" VARIANT=TFX ../../common/build.sh "$build"
  VARIANT=fpsp040 ../../common/build.sh "$build"
  VARIANT=fpsp060 ../../common/build.sh "$build"
else
  ../../common/build.sh "$build"
fi
if [ -n "${OUTPUT_SLAVE:-}" ]; then cp -f "tmp/build/$build/TFX.Slave" "$OUTPUT_SLAVE"; fi
