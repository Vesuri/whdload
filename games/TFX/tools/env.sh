#!/bin/bash
# Sourced from bash by the tools (". tools/env.sh" from the game directory): the shared
# environment (common/env.sh) and HARNESS_ROOT, the game directory.
HARNESS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
. "$HARNESS_ROOT/../../common/env.sh"
export HARNESS_ROOT
