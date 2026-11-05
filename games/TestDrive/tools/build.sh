#!/bin/bash
# The harness's build interface on common/build.sh: tools/build.sh is the release build
# (tmp/build/release/TestDrive.Slave), VERIFY=1 tools/build.sh the VERIFY build
# (tmp/build/verify/TestDrive.Slave), each with its listing (TestDrive.lst) beside it.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "${VERIFY:-0}" = 1 ]; then build=verify; else build=release; fi
unset VERIFY
exec ../../common/build.sh "$build"
