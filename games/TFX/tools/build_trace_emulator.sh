#!/usr/bin/env bash
# Build a private 040 dispatch-trace emulator from a configured native FS-UAE build.
# Input: the existing AmigaXDev fs-uae-arm/fs-uae build directory, never modified.
set -euo pipefail
HARNESS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="${1:?Pass the configured native FS-UAE build directory}"
DEST="$HARNESS_ROOT/tmp/step3-emulator/fs-uae"
[ ! -e "$DEST" ] || { echo "Refusing to overwrite $DEST" >&2; exit 1; }
test -f "$SOURCE/src/newcpu.cpp"
mkdir -p "$(dirname "$DEST")"
cp -a "$SOURCE" "$DEST"
(cd "$DEST" && patch -p1 < "$HARNESS_ROOT/tools/040-dispatch-trace.patch")
make -C "$DEST" -j4 > "$HARNESS_ROOT/tmp/step3-emulator/build.log" 2>&1
shasum -a 256 "$DEST/fs-uae" "$HARNESS_ROOT/tools/040-dispatch-trace.patch"
