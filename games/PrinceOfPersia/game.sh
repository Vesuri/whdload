# Prince of Persia hooks (common/template/game.sh lists them).

# savegame.s includes macros/ntypes.i from the WHDLoad tree's Src/ (the shared build only
# searches Src/sources). Set here, after the shared environment has set WHDLOAD.
VASM_FLAGS="$VASM_FLAGS -I$WHDLOAD/Src"

# savegame.s INCBINs xen_8.bin, the xen/8 Amiga font. It is a binary from the original
# installer archive (PrinceOfPersiaInstall/source/), so it is not tracked: the build takes it
# from the unpacked archive into src/ (ignored), checked against this hash, and the release
# packager ships it in the source drawer as before.
XEN_FONT_SHA256=719ed8338a99ef663e86d79cb28d15d5ec433aea2764690d3b13fa433f5a8cbd

game_build() {
  local font="$GAME_ROOT/src/xen_8.bin" from="$GAME_ROOT/tmp/game/PrinceOfPersiaInstall/source/xen_8.bin"
  if [ ! -f "$font" ] || [ "$(shasum -a 256 "$font" | cut -d' ' -f1)" != "$XEN_FONT_SHA256" ]; then
    [ -f "$from" ] || die "no tmp/game/PrinceOfPersiaInstall/source/xen_8.bin: run make unpack ARCHIVES=<directory> first"
    [ "$(shasum -a 256 "$from" | cut -d' ' -f1)" = "$XEN_FONT_SHA256" ] || die "$from differs from its pinned hash"
    cp -f "$from" "$font"
  fi
  vasm_build "$1" "$2"
}

# Every tool compiles. The harness's checks read captures in tmp/ and are run by hand
# (docs/development.md).
game_check() {
  (
    cd "$GAME_ROOT"
    python3 - <<'EOF' || die "a tool does not compile"
import pathlib, sys
bad = 0
for p in sorted(pathlib.Path('tools').glob('*.py')):
    try:
        compile(p.read_text(), str(p), 'exec')
    except SyntaxError as e:
        print(f'{p}: {e}', file=sys.stderr); bad = 1
sys.exit(bad)
EOF
    echo "compiled: tools/*.py"
    for sh in tools/*.sh; do
      bash -n "$sh" || die "$sh does not parse"
    done
    echo "parsed: tools/*.sh"
  )
}
