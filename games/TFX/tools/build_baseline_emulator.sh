#!/usr/bin/env bash
# Private read-only CPU metadata observer; does not alter emulation or profiling.
set -euo pipefail
HARNESS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="${1:?Pass the configured native FS-UAE build directory}"
DEST="$HARNESS_ROOT/tmp/step4-emulator/fs-uae"
[ ! -e "$DEST" ] || { echo "Refusing to overwrite $DEST" >&2; exit 1; }
test -f "$SOURCE/src/barto_gdbserver.cpp"
mkdir -p "$(dirname "$DEST")"
cp -a "$SOURCE" "$DEST"
(cd "$DEST" && patch -p1 < "$HARNESS_ROOT/tools/cpuinfo-observer.patch")
make -C "$DEST" -j4 > "$HARNESS_ROOT/tmp/step4-emulator/build.log" 2>&1
shasum -a 256 "$DEST/fs-uae" "$HARNESS_ROOT/tools/cpuinfo-observer.patch"
