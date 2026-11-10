# Formula One Grand Prix hooks (common/template/game.sh lists them).

# make run (and tools/f1gp.py serve) on the release slave: "Enhanced frame rate" on, as the
# shipped icons set it (G1), unless WHD_ARGS names CUSTOM2. Other builds and slaves, whose
# CUSTOM2 bits mean something else, are left alone.
game_prepare() {
  [ -z "${SLAVE:-}" ] && [ "${BUILD:-release}" = release ] || return 0
  case " ${WHD_ARGS:-} " in *" CUSTOM2="*) return 0 ;; esac
  WHD_ARGS="${WHD_ARGS:+$WHD_ARGS }CUSTOM2=1"
}

# The build: verify the toolchain and the pinned game, generate the original loader's
# payload and the E2, E4 and F5 tables from the game into tmp/slave/ (derived bytes, never
# committed), then assemble src/F1GP.s. OUT also gets build.json (the slave's and the
# source's SHA-256), which the capture tools check.
game_build() {
  local build="$1" out="$2" defines lib d incs listing
  case "$build" in
    release) defines="${DEFINES_release-}" ;;
    developer) defines="${DEFINES_developer-}" ;;
    verify) defines="${DEFINES_verify-}" ;;
    *) die "BUILD must be release, developer or verify" ;;
  esac
  export NDK_ASM="${NDK_ASM:-$AMIGA_SHARE/ndk/Include_I}"
  python3 tools/slave_toolchain.py > /dev/null
  python3 tools/slave_inputs.py > /dev/null
  python3 tools/e2_tables.py > /dev/null
  python3 tools/e4_tables.py > /dev/null
  python3 tools/f5_sites.py > /dev/null
  mkdir -p tmp/slave/include/lvo
  for lib in dos exec graphics expansion; do
    printf '        INCLUDE "lvo/%s_lib.i"\n' "$lib" > "tmp/slave/include/lvo/$lib.i"
  done
  incs=(-Itmp/slave/include -I"$NDK_ASM" -I"$WHDLOAD/Include" -I"$NDK" -I"$WHDLOAD/Src/sources")
  listing=(-L "$out/$VARIANT.lst")
  defines="$defines ${VASM_EXTRA:-}"
  case " $defines " in *" -L "*) listing=() ;; esac
  # shellcheck disable=SC2086  # flag lists are word-split on purpose
  if ! "$VASM" $defines $VASM_FLAGS "${incs[@]}" -quiet -o "$out/$VARIANT.Slave" \
      ${listing[@]+"${listing[@]}"} "$SOURCE" > "$out/$VARIANT.log" 2>&1; then
    cat "$out/$VARIANT.log" >&2
    rm -f "$out/$VARIANT.Slave"
    die "the $build build of $VARIANT failed (tmp/build/$build/$VARIANT.log)"
  fi
  # The game's own source files the slave was assembled from (not the generated tmp/ ones).
  # shellcheck disable=SC2086
  "$VASM" $defines $VASM_FLAGS "${incs[@]}" -quiet -depend=list -o "$out/$VARIANT.Slave" \
    "$SOURCE" 2>/dev/null |
    while IFS= read -r d; do
      case "$d" in "$GAME_ROOT"/*) d="${d#"$GAME_ROOT"/}" ;; /*|tmp/*) continue ;; esac
      [ -f "$d" ] && printf '%s\n' "$d"
    done | sort -u > "$out/$VARIANT.deps.tmp"
  { printf '%s\n' "$SOURCE"; cat "$out/$VARIANT.deps.tmp"; } | awk '!seen[$0]++' > "$out/$VARIANT.deps"
  rm -f "$out/$VARIANT.deps.tmp"
  python3 - "$out" "$build" "$VARIANT" "$SOURCE" <<'PYMETA'
import hashlib, json, sys
from pathlib import Path
out, build, variant, source = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
meta = dict(build=build, slave_sha256=hashlib.sha256((out/f'{variant}.Slave').read_bytes()).hexdigest(),
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
(out/'build.json').write_text(json.dumps(meta, indent=2)+'\n')
PYMETA
}

# Codetapper's installer archive with the new slave, ReadMe and the game icons' MEMCONFIG
# tooltype (tools/package_release.py).
game_dist() {
  local force=()
  [ "${FORCE:-0}" != 1 ] || force=(--force)
  python3 "$GAME_ROOT/tools/package_release.py" --dist "$1" ${force[@]+"${force[@]}"}
}

# The self-contained unit test (the world clock), and the B4 checks when their captures
# (tmp/b4/verify-off and verify-on, docs/development.md) are present. test_state_diff.py and
# test_profile_anchor.py take capture directories and are run by hand.
game_check() {
  (cd "$GAME_ROOT" && python3 -m unittest -q tools/test_world_clock.py) || return 1
  if [ -d "$GAME_ROOT/tmp/b4/verify-off" ] && [ -d "$GAME_ROOT/tmp/b4/verify-on" ]; then
    (cd "$GAME_ROOT" && python3 tools/test_disabled.py > /dev/null) || return 1
    echo "$GAME: B4 checks passed"
  else
    echo "$GAME: no tmp/b4 captures, B4 checks skipped"
  fi
}
