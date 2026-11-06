#!/usr/bin/env bash
# Input is the configured step4 cpuinfo-observer build, not the shared installation.
set -euo pipefail
HARNESS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="${1:?Pass the configured step4 metadata-observer build directory}"
DEST="$HARNESS_ROOT/tmp/step5-emulator/fs-uae"
[ ! -e "$DEST" ] || { echo "Refusing to overwrite $DEST" >&2; exit 1; }
test -f "$SOURCE/src/barto_gdbserver.cpp"
mkdir -p "$(dirname "$DEST")"
cp -a "$SOURCE" "$DEST"
(cd "$DEST" && patch -p1 < "$HARNESS_ROOT/tools/040-cost-observer.patch")
make -C "$DEST" -j4 > "$HARNESS_ROOT/tmp/step5-emulator/build.log" 2>&1
shasum -a 256 "$DEST/fs-uae" "$HARNESS_ROOT/tools/040-cost-observer.patch"
