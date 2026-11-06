# TFX hooks (common/template/game.sh lists them). They keep the run options of the fork
# harness's amiga/run.sh, which the tools in tools/ use:
#   FPSP040=path FPSP060=path   replace data/fpsp040, data/fpsp060 on the game drive
#   EXTRA_FILES='a b'           host files copied to DH1: (e.g. a program for RUN_CMD)
#   RUN_CMD='calib040 >DH1:calib.txt'   run this instead of WHDLoad
#   HDF=1 [HDF_SEED=dir]        boot from disk images packed from the drives (xdftool);
#                               deterministic replays deadlock on directory drives.
#                               HDF_SEED reuses (or saves) the images in dir
#   EXTRA_ARGS                  default --zorro_iii_memory=32768 (the target's 32 MB)

game_prepare() {
  case "$VARIANT" in
    fpsp040|fpsp060) die "$VARIANT is not a slave; run VARIANT=TFX (FPSP040=/FPSP060= replace the FPSPs)" ;;
  esac
  EXTRA_ARGS="${EXTRA_ARGS---zorro_iii_memory=32768}"
  export EXTRA_ARGS
  if [ "${JOY0:-}" != none ]; then JOY0_MODE="${JOY0_MODE:-mouse}"; fi
}

# The FPSP replacements, extra files and SetPatch (the harness ran it before WHDLoad).
game_drives() {
  local dh0="$1" dh1="$2" f
  [ -z "${FPSP040:-}" ] || cp -f "$(caller_path "$FPSP040")" "$dh1/data/fpsp040"
  [ -z "${FPSP060:-}" ] || cp -f "$(caller_path "$FPSP060")" "$dh1/data/fpsp060"
  for f in ${EXTRA_FILES:-}; do cp -f "$(caller_path "$f")" "$dh1/"; done
  mkdir -p "$dh0/c"
  cp -f "$SETPATCH" "$dh0/c/SetPatch"
  chmod -R u+w "$dh0" "$dh1"
}

# After common/run.sh has written the startup-sequence: SetPatch before the shell lines,
# RUN_CMD instead of WHDLoad, then the disk images for HDF=1. The images go ahead of
# run.sh's directory drives in FSUAE_SETUP_ARGS, so FS-UAE uses them (first value wins).
# The launcher may set the machine up more than once; the drives are changed only once.
game_setup() {
  local h0="$FSUAE_RUN/dh0.hdf" h1="$FSUAE_RUN/dh1.hdf"
  if [ -z "${TFX_DRIVES_DONE:-}" ]; then
    TFX_DRIVES_DONE=1
    tfx_drives "$h0" "$h1"
  fi
  [ "${HDF:-0}" = 1 ] || return 0
  FSUAE_SETUP_ARGS=(--hard_drive_0="$h0" --hard_drive_1="$h1"
    ${FSUAE_SETUP_ARGS[@]+"${FSUAE_SETUP_ARGS[@]}"})
}

tfx_drives() {
  local h0="$1" h1="$2" seq="$DH0/s/startup-sequence" tmp="$DH0/s/startup-sequence.new"
  awk -v cmd="${RUN_CMD:-}" '
    /^Stack / && !sp { print "DH0:c/SetPatch QUIET"; sp = 1 }
    /^WHDLoad / && cmd != "" { print cmd; next }
    { print }' "$seq" > "$tmp"
  mv "$tmp" "$seq"
  [ "${HDF:-0}" = 1 ] || return 0
  if [ -n "${HDF_SEED:-}" ] && [ -f "$HDF_SEED/dh0.hdf" ]; then
    cp "$HDF_SEED/dh0.hdf" "$h0"
    cp "$HDF_SEED/dh1.hdf" "$h1"
  else
    command -v xdftool > /dev/null || die "HDF=1 needs xdftool (amitools)"
    rm -f "$h0" "$h1"
    xdftool -f "$h0" pack "$DH0" DOS1 size=8Mi > /dev/null
    xdftool -f "$h1" pack "$DH1" DOS1 size=64Mi > /dev/null
    if [ -n "${HDF_SEED:-}" ]; then
      mkdir -p "$HDF_SEED"
      cp "$h0" "$h1" "$HDF_SEED/"
    fi
  fi
}

# Each archive is unpacked into a drawer named after it, as the harness had them:
# tmp/game/TFX_v2.1_AGA/TFXAGA is the installed game that runs, tmp/game/TFX/TFXInstall
# the installer package.
game_unpack() {
  local sum name base stage
  while read -r sum name; do
    case "$sum" in ''|'#'*) continue ;; esac
    case "$name" in *.lha) ;; *) continue ;; esac
    base="${name%.lha}"
    if [ -e "tmp/game/$base" ]; then
      if [ "${FORCE:-0}" = 1 ]; then rm -rf "tmp/game/$base"; else
        echo "kept the existing tmp/game/$base (FORCE=1 replaces it)"; continue
      fi
    fi
    stage="$(mktemp -d "$GAME_ROOT/tmp/unpack.XXXXXX")"
    "$LHA" "xqw=$stage" "tmp/archives/$name"
    mv "$stage" "tmp/game/$base"
    echo "unpacked tmp/game/$base"
  done < inputs.sha256
}

# Every Python tool compiles and every shell tool parses. The captures and twin tests need
# the emulator and the evidence in tmp/; they are run by hand (docs/development.md).
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
    for f in tools/*.sh; do bash -n "$f" || die "$f does not parse"; done
    echo "parsed: tools/*.sh"
  )
}
