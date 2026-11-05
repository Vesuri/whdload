#!/usr/bin/env bash
# The harness's launcher, the run script of every capture and check (amigaxdev's Server):
# common/run.sh with the slave named explicitly and the harness's A500 (512 KB chip, 1.5 MB
# slow) unless the caller's CPU, AMIGA_MODEL, CHIP_KB, SLOW_KB, FAST_KB, KICKSTART or FSUAE
# say otherwise. It also writes tmp/run/<instance>/.run/launch.json. FF1_LAUNCH selects
# stdio, diagnostic or session (game.sh).
set -euo pipefail
: "${SLAVE:?Set SLAVE explicitly to the shipped or a rebuilt slave}"
export SETUP=custom FF1_HARNESS=1
exec "$(cd "$(dirname "$0")/../../.." && pwd)/common/run.sh" run
