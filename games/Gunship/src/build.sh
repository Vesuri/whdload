#!/usr/bin/env bash
# Build both release slaves with the shared AmigaXDev toolchain.
set -euo pipefail
source "${AMIGA_ENV:-$HOME/.local/share/amiga/env.sh}"
source_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(git -C "$source_dir" rev-parse --show-toplevel)"
output_dir="${BUILD_DIR:-$repo_root/tmp/dev/tmp/build/release}"
mkdir -p "$output_dir/include/lvo"
for lib in dos exec graphics expansion; do
  printf ' IFND GS_LVO_%s\nGS_LVO_%s SET 1\n INCLUDE "lvo/%s_lib.i"\n ENDC\n' "$lib" "$lib" "$lib" > "$output_dir/include/lvo/$lib.i"
done
cd "$source_dir"
for version in PAL NTSC; do
  defines=()
  name=Gunship
  if [ "$version" = NTSC ]; then defines+=(-DGUNSHIP_NTSC=1); name=GunshipNTSC; fi
  if [ "${VERIFY:-0}" = 1 ]; then defines+=(-DVERIFY=1); name+="-verify"; fi
  "$VASM" "${defines[@]}" -m68000 -pic -x -devpac -Fhunkexe -nosym \
    -I"$output_dir/include" -I"$WHDLOAD/Include" -I"$WHDLOAD/Src" \
    -I"$WHDLOAD/Src/sources" -I"$AMIGA_SHARE/ndk/Include_I" \
    -L "$output_dir/$name.slave.lst" -o "$output_dir/$name.slave" GunshipHD.s
 done
