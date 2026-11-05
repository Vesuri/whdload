#!/bin/bash
# Sourced from bash by the tools' shell scripts: the shared environment (common/env.sh) and
# the harness variables. HARNESS_ROOT is the game directory, TD_GAME the installed drawer
# the tools read.
HARNESS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
. "$HARNESS_ROOT/../../common/env.sh"
GAME_SOURCE="$HARNESS_ROOT/src"
TD_GAME="${TD_GAME:-$HARNESS_ROOT/tmp/game/TestDrive_v1.3_0089/TestDrive}"
SLAVE_NAME=TestDrive.slave
export HARNESS_ROOT GAME_SOURCE TD_GAME SLAVE_NAME
