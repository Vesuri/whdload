# Test Drive hooks (common/template/game.sh lists them).

# TD_SETUP=a500|a1200|a1200-030: Test Drive II's reference machines, which the harness's
# captures and baselines use. a500: 68000, 512 KB chip, 1.5 MB slow RAM, Kickstart 3.1 A600
# ROM; a1200: 68EC020, 2 MB chip, 4 MB fast; a1200-030: that with a cycle-exact 25 MHz
# 68030. Not with a named SETUP.
game_prepare() {
  case "${TD_SETUP:-}" in
    '') return 0 ;;
    a500|a1200|a1200-030) ;;
    *) die "unknown TD_SETUP: $TD_SETUP (a500, a1200 or a1200-030)" ;;
  esac
  [ -z "${AMIGA_SETUP:-}" ] || die "use TD_SETUP or SETUP, not both"
  AMIGA_MODEL=A500 CPU=68000 CHIP_KB=512 FAST_KB=0 SLOW_KB=1536
  KICKSTART="$AMIGA_SHARE/Kickstarts/kick40063.A600"
  if [ "$TD_SETUP" != a500 ]; then
    AMIGA_MODEL=A1200 CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 SLOW_KB=0
    KICKSTART="$KICKSTART_A1200"
  fi
  if [ "$TD_SETUP" = a1200-030 ]; then
    CPU=68030
    EXTRA_ARGS="--uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true ${EXTRA_ARGS:-}"
  fi
  export AMIGA_MODEL CPU CHIP_KB FAST_KB SLOW_KB KICKSTART EXTRA_ARGS
}

# The effective machine, as the harness's captures read it (.run/machine.json): FS-UAE keeps
# the first value of an option, so EXTRA_ARGS, then the named machine's, then the
# variables'.
game_setup() {
  python3 "$GAME_ROOT/tools/record_machine.py" "$FSUAE_RUN/machine.json" \
    ${EXTRA_ARGS:-} ${FSUAE_SETUP_ARGS[@]+"${FSUAE_SETUP_ARGS[@]}"} \
    --amiga_model="$AMIGA_MODEL" --cpu="$CPU" --chip_memory="$CHIP_KB" \
    --fast_memory="$FAST_KB" --slow_memory="${SLOW_KB:-0}"
}

# Both archives hold a TestDrive drawer, so each is unpacked into a drawer named after it:
# tmp/game/TestDrive_v1.3_0089/TestDrive is the installed game that runs,
# tmp/game/TestDrive/TestDriveInstall the installer package.
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

# Every tool compiles, and the static checks that need only the source, the builds and the
# installed game pass: the overlay hook audit, the simulation and renderer patch-range
# audits, the audio audit, the phase-8 arithmetic and the simulation budget unit tests. The
# capture checks read evidence in tmp/ and are run by hand (docs/development.md).
GAME_CHECKS="audit_overlay.py audit_simulation.py audit_render.py audit_audio.py
  phase8_math.py test_simulation_budget.py"

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
    if [ ! -d tmp/game/TestDrive_v1.3_0089/TestDrive ]; then
      echo "skipped (no installed game; make unpack): $GAME_CHECKS"
      exit 0
    fi
    "$COMMON/build.sh" verify > /dev/null
    for test in $GAME_CHECKS; do
      log="tmp/check-${test%.py}.log"
      python3 "tools/$test" > "$log" 2>&1 || { cat "$log" >&2; die "tools/$test failed ($log)"; }
      echo "passed: tools/$test"
    done
  )
}
