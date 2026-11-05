#!/usr/bin/env bash
# Private native FS-UAE for this harness: AmigaXDev's native build (core fix, CPU frequency,
# harness `monitor key`/`fields`/whole-space profile, register observer, aprof) plus
# tools/patches/fsuae-input.patch (Ferrari Formula One's `monitor input EVENT VALUE`, e.g.
# JOY2_UP / JOY2_FIRE_BUTTON, and `monitor mouse`). Installs tmp/emulator/fs-uae.
# The build happens in $FSUAE_BUILD (default tmp/fsuae-build); autotools breaks on spaces in it.
set -euo pipefail
HARNESS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"   # the game directory
. "$HARNESS_ROOT/../../common/env.sh"
AXD="${AMIGAXDEV:?set AMIGAXDEV to the AmigaXDev checkout (its manifest/ and patches/)}"
SHARED_SRC="$AMIGA_SHARE/fs-uae-aprof-build/fs-uae"   # clone source (has the pinned commit)
DEPS="$AMIGA_SHARE/fs-uae-aprof-build/deps"           # static SDL2_ttf and libmpeg2
B="${FSUAE_BUILD:-$HARNESS_ROOT/tmp/fsuae-build}"; B="${B%/}"
OUT="$HARNESS_ROOT/tmp/emulator"
case "$B" in *' '*) echo "build path has spaces: $B" >&2; exit 1 ;; esac
PATH="/opt/homebrew/bin:$PATH"
commit=$(awk -F'\t' '$1 == "fs-uae-barto" {print $2}' "$AXD/manifest/git.tsv")
[ -d "$B/.git" ] || git clone -q "$SHARED_SRC" "$B"
git -C "$B" checkout -q --force "$commit"
git -C "$B" clean -qfdx
for p in fsuae-mmu-write-cache fsuae-cpu-frequency fsuae-harness fsuae-register-observer fsuae-aprof; do
  git -C "$B" apply "$AXD/patches/$p.patch"
done
patch -d "$B" -p1 --no-backup-if-mismatch < "$HARNESS_ROOT/tools/patches/fsuae-input.patch"
export PKG_CONFIG_PATH="$DEPS/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
(cd "$B" && ./bootstrap && ./configure --disable-jit --disable-x86 \
   SDL2_TTF_CFLAGS="-I$DEPS/include $(pkg-config --cflags SDL2_ttf)" SDL2_TTF_LIBS="$(pkg-config --static --libs SDL2_ttf freetype2)" \
   LIBMPEG2_CFLAGS="$(pkg-config --cflags libmpeg2)" LIBMPEG2_LIBS="$(pkg-config --static --libs libmpeg2 libmpeg2convert)" \
   CFLAGS=-O2 CXXFLAGS=-O2 && make -j"$(sysctl -n hw.ncpu)") > "$B.log" 2>&1 || { echo "build failed, see $B.log" >&2; exit 1; }
rm -rf "$OUT"; mkdir -p "$OUT"
cp -f "$B/fs-uae" "$B/fs-uae.dat" "$OUT/"; cp -R "$B/data" "$OUT/data"
{ echo "commit $commit"; for p in fsuae-mmu-write-cache fsuae-cpu-frequency fsuae-harness fsuae-register-observer fsuae-aprof; do
    echo "$p $(shasum -a 256 "$AXD/patches/$p.patch" | cut -d' ' -f1)"; done
  echo "fsuae-input $(shasum -a 256 "$HARNESS_ROOT/tools/patches/fsuae-input.patch" | cut -d' ' -f1)"
  echo "fs-uae $(shasum -a 256 "$OUT/fs-uae" | cut -d' ' -f1)"; } > "$OUT/source-revision.txt"
cat "$OUT/source-revision.txt"
