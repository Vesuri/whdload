# Stellar 7 hooks (common/template/game.sh lists them).

# The release slave (Stellar7) carries both fixed-rate simulations. Unless the build
# compiles one in itself (-DSIM60), assemble each alone from src/payload.s into
# OUT/Stellar7.<name>.bin and .lst; src/Stellar7.s includes them. Each takes its development
# variant's defines (game.conf) and the -D words of VASM_EXTRA. Each is always a release
# simulation: a VERIFY simulation needs the VERIFY slave's own symbols, so a verify build
# of Stellar7 has the fixtures in its loader only.
game_build() {
  local build="$1" out="$2" defines extra="" word name payload_defines incs inc
  case "$build" in
    release) defines="${DEFINES_release-}" ;;
    verify) defines="${DEFINES_verify--DVERIFY=1}" ;;
    developer) defines="${DEFINES_developer--DDEVELOPER=1}" ;;
    *) eval "defines=\"\${DEFINES_$build-}\"" ;;
  esac
  case "$VARIANT: ${DEFINES:-} $defines ${VASM_EXTRA:-} " in
    *" -DSIM60"*|Stellar7-*) vasm_build "$build" "$out"; return ;;
  esac
  for word in ${VASM_EXTRA:-}; do
    case "$word" in -D*) extra="$extra $word" ;; esac
  done
  incs=(-I"$GAME_ROOT/src")
  for inc in ${INCLUDES:-}; do incs+=(-I"$GAME_ROOT/$inc"); done
  incs+=(-I"$AMIGA_INCLUDE" -I"$WHDLOAD/Include" -I"$WHDLOAD/Src/sources" -I"$NDK")
  : > "$out/$VARIANT.payload-deps"
  for name in Sim68000 Sim60; do
    if [ "$name" = Sim60 ]; then payload_defines="$SIM60_DEFINES"; else payload_defines="$SIM68000_DEFINES"; fi
    payload="$out/$VARIANT.$name"
    rm -f "$payload.bin"
    # shellcheck disable=SC2086  # flag lists are word-split on purpose
    if ! "$VASM" -m68000 -pic -x -devpac -Fbin -nosym $payload_defines $extra "${incs[@]}" -quiet \
        -o "$payload.bin" -L "$payload.lst" src/payload.s > "$payload.log" 2>&1; then
      cat "$payload.log" >&2
      rm -f "$payload.bin"
      die "the $name simulation for the $build build failed (tmp/build/$build/${payload##*/}.log)"
    fi
    # shellcheck disable=SC2086
    "$VASM" -m68000 -pic -x -devpac -Fbin -nosym $payload_defines $extra "${incs[@]}" -quiet -depend=list \
      -o "$payload.bin" src/payload.s 2>/dev/null >> "$out/$VARIANT.payload-deps"
  done
  VASM_EXTRA="${VASM_EXTRA:-} -I$out" vasm_build "$build" "$out"
  # The archive source lists the simulation sources, not the assembled payloads.
  { cat "$out/$VARIANT.deps"
    while IFS= read -r inc; do
      case "$inc" in "$GAME_ROOT"/*) inc="${inc#"$GAME_ROOT"/}" ;; /*) continue ;; esac
      [ -f "$inc" ] && printf '%s\n' "$inc"
    done < "$out/$VARIANT.payload-deps"
  } | grep -v '^tmp/' | awk '!seen[$0]++' > "$out/$VARIANT.deps.tmp"
  mv "$out/$VARIANT.deps.tmp" "$out/$VARIANT.deps"
  rm -f "$out/$VARIANT.payload-deps"
}

# The installer archive: tools/package_release.py edits the original installer to install
# the release slave.
game_dist() {
  python3 "$GAME_ROOT/tools/package_release.py" --dist "$1"
}

# The quick unit tests; the emulator-driven checks are run by hand (docs/development.md).
game_check() {
  (cd "$GAME_ROOT" && python3 -m unittest discover -s tools -p 'test_*.py' -q)
}
