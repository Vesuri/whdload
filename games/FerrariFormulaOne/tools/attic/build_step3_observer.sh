#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VARIANT="${1:-survey}"
case "$VARIANT" in survey) NAME=fs-uae;; events) NAME=fs-uae-events;; controls) NAME=fs-uae-controls;; *) exit 2;; esac
BUILD="$ROOT/tmp/step3/emulator-$VARIANT-build"
if [ ! -d "$BUILD" ]; then cp -R "$ROOT/tmp/step2/emulator-build" "$BUILD"; fi
cp "$ROOT/tmp/step3/barto-before.cpp" "$BUILD/src/barto_gdbserver.cpp"
patch -d "$BUILD" -p1 < "$ROOT/tools/step3-observer-$VARIANT.patch"
make -C "$BUILD" -W src/barto_gdbserver.cpp fs-uae -j4 > "$BUILD/step3-build.log" 2>&1
cp "$BUILD/fs-uae" "$ROOT/tmp/step3/$NAME"
for resource in share data fsemu; do
 if [ ! -e "$ROOT/tmp/step3/$resource" ]; then ln -s "$BUILD/$resource" "$ROOT/tmp/step3/$resource"; fi
done
shasum -a 256 "$ROOT/tmp/step3/$NAME"
