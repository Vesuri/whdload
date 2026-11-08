#!/bin/bash
# Build the measurement emulator most checks run on (RELEASE_FSUAE default,
# tmp/step5-frame-observer-build/fs-uae): Graham Bates' FS-UAE (barto gdb stub) at
# b70b1180b44ab25b97cd66466c70879897d8a362 plus tools/observer.patch:
#   - gdb monitor commands census, survey, blits, warp, warp-status, mouse, input, irq-state
#   - the 030/040/060 clock fix: (uae_u64)CYCLE_UNIT * (baseclock / 8) / cpu_frequency
#     (RELEASE_QUALIFICATION.md "Accelerated clock calibration")
#   - FF1 keyboard and input helpers
# Nothing is downloaded: SRC is a local checkout of that commit (the game's ignored
# tmp/step2/emulator-build is one), copied to tmp/fs-uae-observer-build. A configured tree
# keeps its Makefile; a fresh one is configured with the static SDL2_ttf/libmpeg2 that
# AmigaXDev's build-fsuae.sh leaves in its deps directory (include/ and lib/):
#   tools/build_observer.sh SRC DEPS_DIR
set -euo pipefail
cd "$(dirname "$0")/.."
src0="${1:?usage: tools/build_observer.sh SRC DEPS_DIR}"
deps="${2:?usage: tools/build_observer.sh SRC DEPS_DIR}"
src=tmp/fs-uae-observer-build
[ -d "$src" ] || cp -R "$src0" "$src"
[ "$(git -C "$src" rev-parse HEAD)" = b70b1180b44ab25b97cd66466c70879897d8a362 ] \
  || { echo "$src is not at b70b1180" >&2; exit 1; }
git -C "$src" checkout -q -- src
git -C "$src" apply "$PWD/tools/observer.patch"
(cd "$src" && { [ -f Makefile ] || { ./bootstrap && ./configure \
  SDL2_TTF_CFLAGS="-I$deps/include" SDL2_TTF_LIBS="$deps/lib/libSDL2_ttf.a $(pkg-config --static --libs freetype2)"; }; } \
  && make -j8 fs-uae >observer-build.log 2>&1) || { tail -20 "$src/observer-build.log"; exit 1; }
ln -sfn fs-uae-observer-build tmp/step5-frame-observer-build
shasum -a 256 "$src/fs-uae"
