#!/bin/bash
# Build the slave with extra vasm flags, for the tools and docs that name an output file:
#   OUTPUT_SLAVE=tmp/build/NAME.slave tools/build.sh [-DVERIFY_X=1 ...] [-L tmp/build/NAME.lst]
# The build is common/build.sh's (make build BUILD=NAME VASM_EXTRA='...'), in
# tmp/build/<NAME>/, copied to OUTPUT_SLAVE (default tmp/build/HardDrivin.Slave). NAME is
# tool_ and OUTPUT_SLAVE's base name, so builds with different outputs can run at the same
# time. Only letters, digits and underscores: common/build.sh reads DEFINES_<NAME>, which a
# hyphen in NAME would turn into a default-value expansion.
# The flags are word-split: listing paths must not contain spaces.
set -eu
GAME_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
out="${OUTPUT_SLAVE:-$GAME_ROOT/tmp/build/HardDrivin.Slave}"
case "$out" in /*) ;; *) out="$PWD/$out" ;; esac
name="$(basename "$out")"
name="tool_$(printf '%s' "${name%.*}" | tr -c 'A-Za-z0-9_' '_')"
mkdir -p "$(dirname "$out")"
VASM_EXTRA="$*" VARIANT=HardDrivin GAME=HardDrivin "$GAME_ROOT/../../common/build.sh" "$name" > /dev/null
cp -f "$GAME_ROOT/tmp/build/$name/HardDrivin.Slave" "$out"
echo "$out"
