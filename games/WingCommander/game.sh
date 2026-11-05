# Wing Commander hooks (common/template/game.sh lists them).

# The slaves are generated: tools/reconstruct.py (CD32) and tools/ocs_memory_build.py (the
# OCS public candidate) disassemble the pinned original slave from tmp/game/, add the
# src/ modules and assemble the result. Each run writes a fresh directory, kept as
# OUT/<Variant>/ (build.json, slave.lst, payload.bin, ReadMe, the OCS icon) for the
# checking and packaging tools; the slave and listing are copied beside it.
#   release      CD32 --release (2.0b public options); OCS --public (2.0b, CUSTOM5 toggle)
#   verify       CD32 --verify, the CUSTOM1=2 diagnostic seam
#   reconstruct  the original slave, reassembled and checked byte for byte
#   render, render-control, render-verify   CD32 rendering adapter diagnostics
game_build() {
  local build="$1" out="$2" tool args=()
  case "$VARIANT:$build" in
    WingCommanderCD32:release) tool=reconstruct.py args=(--variant cd32 --release) ;;
    WingCommanderCD32:verify) tool=reconstruct.py args=(--variant cd32 --verify) ;;
    WingCommanderCD32:reconstruct) tool=reconstruct.py args=(--variant cd32) ;;
    WingCommanderCD32:render) tool=reconstruct.py args=(--variant cd32 --render) ;;
    WingCommanderCD32:render-control) tool=reconstruct.py args=(--variant cd32 --render-control) ;;
    WingCommanderCD32:render-verify) tool=reconstruct.py args=(--variant cd32 --render --render-verify) ;;
    WingCommander:release) tool=ocs_memory_build.py args=(--public) ;;
    WingCommander:reconstruct) tool=reconstruct.py args=(--variant ocs) ;;
    *) die "no $build build of $VARIANT (game.sh game_build lists the builds)" ;;
  esac
  local stage="$out/$VARIANT.new"
  rm -rf "$stage" "$out/$VARIANT.Slave"
  if ! (cd "$GAME_ROOT" && python3 "tools/$tool" "${args[@]}" --output "$stage") > "$out/$VARIANT.log" 2>&1; then
    cat "$out/$VARIANT.log" >&2
    rm -rf "$stage"
    die "the $build build of $VARIANT failed (tmp/build/$build/$VARIANT.log)"
  fi
  rm -rf "${out:?}/$VARIANT"
  mv "$stage" "$out/$VARIANT"
  cp "$out/$VARIANT/$VARIANT.Slave" "$out/$VARIANT.Slave"
  if [ -f "$out/$VARIANT/slave.lst" ]; then cp "$out/$VARIANT/slave.lst" "$out/$VARIANT.lst"; fi
  # The generators read the slave modules in src/ and the tables in tools/manifest/.
  (cd "$GAME_ROOT" && find src tools/manifest -type f | LC_ALL=C sort) > "$out/$VARIANT.deps"
}

# Run defaults (they apply only to what the caller did not set):
# - a build (no SLAVE) gets the release options: CD32 CUSTOM5=0 DCACHE, OCS CUSTOM5=1 DCACHE
#   (the Enhanced framerate toggle; on 68000/68010 or without true Fast RAM the slave keeps
#   the original behaviour). WHD_ARGS= (empty) selects the original behaviour;
# - an explicit OCS SLAVE (original or a diagnostic build) boots the A500 baseline, which
#   game_setup gives 4 MB of Zorro II Fast RAM and no slow RAM;
# - 68040 and 68060 machines use FSUAE_MMU: the pinned core takes CHIP write cache
#   attributes from the wrong MMU cache entry, which FSUAE_MMU corrects (it is the binary
#   tools/build_mmu_fix.py builds). Other machines use FSUAE_ARM.
# A recorded emulator that another directory started is never stopped, by a run or make stop.
game_prepare() {
  if [ -z "${SLAVE:-}" ]; then
    if ! user_set WHD_ARGS; then
      case "$VARIANT" in
        WingCommanderCD32) WHD_ARGS="CUSTOM5=0 DCACHE" ;;
        WingCommander) WHD_ARGS="CUSTOM5=1 DCACHE" ;;
      esac
    fi
  elif [ "$VARIANT" = WingCommander ] && ! user_set SETUP && ! user_set AMIGA_SETUP; then
    AMIGA_SETUP=a500
  fi
  if [ -z "${FSUAE:-}" ]; then
    case "$AMIGA_SETUP" in
      a1200-040|a1200-060)
        FSUAE="$FSUAE_MMU"
        [ -x "$FSUAE" ] || die "no FSUAE_MMU emulator at $FSUAE (AmigaXDev; tools/build_mmu_fix.py builds the same correction into tmp/fsuae-mmu-fixed, then pass FSUAE=)"
        ;;
      *) FSUAE="$FSUAE_ARM" ;;
    esac
  fi
  export FSUAE WHD_ARGS AMIGA_SETUP
  wc_check_owner
}

game_stop() { wc_check_owner; }

# A pid file alone does not prove ownership: the pid may since belong to another
# project's emulator.
wc_check_owner() {
  local run="$GAME_ROOT/tmp/run/${INSTANCE:-default}" tracked
  if [ -f "$run/.run/fsuae.pid" ]; then
    tracked="$(cat "$run/.run/fsuae.pid")"
    if (cd "$run" && FSUAE_RUN=.run && . "$FSUAE_COMMON" && fsuae_is_a "$tracked" fs-uae &&
        ! fsuae_is_ours "$tracked"); then
      die "the recorded emulator (pid $tracked) belongs to another directory; refusing to stop it"
    fi
  fi
}

# The archive's slave stays beside a replaced one as <drawer>.original. A public OCS slave
# gets the generated launch icon with its Enhanced framerate tooltype.
game_drives() {
  local dh1="$2"
  if ! cmp -s "$GAME_ROOT/tmp/game/$GAME_DIR/$SLAVE_FILE" "$dh1/$SLAVE_FILE"; then
    cp "$GAME_ROOT/tmp/game/$GAME_DIR/$SLAVE_FILE" "$dh1/$GAME_DIR.original"
  fi
  if [ "$VARIANT" = WingCommander ]; then
    python3 -I -c '
import sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
slave, icon = Path(sys.argv[2]), Path(sys.argv[3])
if b"C5:B:Enhanced framerate (68020+Fast RAM);" in slave.read_bytes():
    from ocs_icon import enhanced_icon
    icon.write_bytes(enhanced_icon(icon.read_bytes()))
' "$GAME_ROOT/tools" "$dh1/$SLAVE_FILE" "$dh1/WingCommander.info"
  fi
}

# The machine edits the harness selects by environment, applied in this order after the
# named machine (docs/development.md describes each):
#   INTRO_STOCK_CLOCK=1        a1200-fast at the stock 020 multiplier (4), no numeric frequency
#   OCS_STOCK_CLOCK=1          the OCS variant on a500 (or a1200-fast with OCS_COMPAT_AGA=1)
#                              at the core's native clock
#   WC_NOMMU_CORE=1            the NOMMU timing cores of a1200-030/040/060, cycle exact
#   WC_BASELINE_CACHE_MODEL=1  the earlier 030+ model: no data cache, no indirect UAE board
#   WC_CPU_SPEED=real|max      the CPU speed of a non-cycle-exact machine
#   WC_INSTANT_BLITTER=0|1     immediate blits (always set explicitly; default 0)
#   OCS on a500                4 MB of Zorro II Fast RAM and no slow RAM
game_setup() {
  local i arg kept=()
  if [ "${INTRO_STOCK_CLOCK:-0}" = 1 ]; then
    [ "$AMIGA_SETUP" = a1200-fast ] || { echo "intro clock requires a1200-fast" >&2; return 1; }
    # A numeric frequency overflows in the pinned core; the stock 020 uses multiplier 4.
    for i in "${!FSUAE_SETUP_ARGS[@]}"; do
      case "${FSUAE_SETUP_ARGS[$i]}" in
        --uae_cpu_multiplier=*) FSUAE_SETUP_ARGS[$i]=--uae_cpu_multiplier=4 ;;
        --uae_cpu_frequency=*) FSUAE_SETUP_ARGS[$i]=--uae_cpu_frequency=0 ;;
      esac
    done
  fi
  if [ "${OCS_STOCK_CLOCK:-0}" = 1 ]; then
    # Zero frequency and multiplier select CYCLE_UNIT/2, the native PAL 68000 clock.
    [ "$VARIANT" = WingCommander ] || return 1
    case "$AMIGA_SETUP:${OCS_COMPAT_AGA:-0}" in a500:0|a1200-fast:1) ;; *) return 1 ;; esac
    for i in "${!FSUAE_SETUP_ARGS[@]}"; do
      case "${FSUAE_SETUP_ARGS[$i]}" in
        --uae_cpu_multiplier=*) FSUAE_SETUP_ARGS[$i]=--uae_cpu_multiplier=0
          [ "${OCS_COMPAT_AGA:-0}" != 1 ] || FSUAE_SETUP_ARGS[$i]=--uae_cpu_multiplier=8
          ;;
        --uae_cpu_frequency=*) FSUAE_SETUP_ARGS[$i]=--uae_cpu_frequency=0 ;;
      esac
    done
  fi
  # Timing-core selection is independent of WHDLoad's NoMMU tooltype.
  if [ "${WC_NOMMU_CORE:-0}" = 1 ]; then
    case "$AMIGA_SETUP" in
      a1200-030) CPU=68EC030 ;;
      a1200-040) CPU=68040-NOMMU ;;
      a1200-060) CPU=68060-NOMMU ;;
      *) echo "NOMMU timing core requires an accelerated preset" >&2; return 1 ;;
    esac
    for i in "${!FSUAE_SETUP_ARGS[@]}"; do
      case "${FSUAE_SETUP_ARGS[$i]}" in
        --cpu=*) FSUAE_SETUP_ARGS[$i]=--cpu="$CPU" ;;
        --uae_mmu_model=*) FSUAE_SETUP_ARGS[$i]=--uae_mmu_model=0 ;;
        --uae_cpu_cycle_exact=*|--uae_cpu_memory_cycle_exact=*|--uae_blitter_cycle_exact=*)
          FSUAE_SETUP_ARGS[$i]="${FSUAE_SETUP_ARGS[$i]%%=*}=true" ;;
      esac
    done
  fi
  # The established 030 measurement baseline: the shared presets' data cache and indirect
  # UAE board do not boot the retained observer build.
  if [ "${WC_BASELINE_CACHE_MODEL:-0}" = 1 ]; then
    case "$AMIGA_SETUP" in
      a1200-030|a1200-040|a1200-060) ;;
      *) echo "baseline cache model requires an accelerated preset" >&2; return 1 ;;
    esac
    for arg in "${FSUAE_SETUP_ARGS[@]}"; do
      case "$arg" in
        --uae_cpu_data_cache=*) kept+=(--uae_cpu_data_cache=false) ;;
        --uae_uaeboard=full+indirect) ;;
        *) kept+=("$arg") ;;
      esac
    done
    FSUAE_SETUP_ARGS=("${kept[@]}")
  fi
  # "max" runs the non-cycle-exact CPU as fast as the host allows against unchanged
  # emulated chipset timing.
  if [ -n "${WC_CPU_SPEED:-}" ]; then
    case "$WC_CPU_SPEED" in real|max) ;; *) echo "WC_CPU_SPEED must be real or max" >&2; return 1 ;; esac
    for i in "${!FSUAE_SETUP_ARGS[@]}"; do
      case "${FSUAE_SETUP_ARGS[$i]}" in
        --uae_cpu_cycle_exact=true) echo "WC_CPU_SPEED requires a non-cycle-exact preset" >&2; return 1 ;;
        --uae_cpu_speed=*) FSUAE_SETUP_ARGS[$i]=--uae_cpu_speed="$WC_CPU_SPEED" ;;
      esac
    done
  fi
  # The ceiling intervention, set explicitly, including the normal control value.
  local immediate=false found=0
  case "${WC_INSTANT_BLITTER:-0}" in
    0) ;;
    1) immediate=true ;;
    *) echo "WC_INSTANT_BLITTER must be 0 or 1" >&2; return 1 ;;
  esac
  for i in "${!FSUAE_SETUP_ARGS[@]}"; do
    case "${FSUAE_SETUP_ARGS[$i]}" in
      --uae_immediate_blits=*) FSUAE_SETUP_ARGS[$i]=--uae_immediate_blits="$immediate"; found=1 ;;
    esac
  done
  [ "$found" = 1 ] || FSUAE_SETUP_ARGS+=(--uae_immediate_blits="$immediate")
  # The native OCS baseline: true Zorro II Fast RAM, no trapdoor slow RAM.
  if [ "$VARIANT" = WingCommander ] && [ "$AMIGA_SETUP" = a500 ]; then
    FAST_KB=4096 SLOW_KB=0
    for i in "${!FSUAE_SETUP_ARGS[@]}"; do
      case "${FSUAE_SETUP_ARGS[$i]}" in
        --fast_memory=*) FSUAE_SETUP_ARGS[$i]=--fast_memory=4096 ;;
        --slow_memory=*) FSUAE_SETUP_ARGS[$i]=--slow_memory=0 ;;
      esac
    done
  fi
}

# The installer archive: Psygore's installer with the new Install script, ReadMe and both
# release slaves (tools/release_install.py stages and checks it), packed with LHa.
game_dist() {
  local dist="$1" version stage archive
  version="$(sed -n 's/^ *Version \([^ ]*\) (.*/\1/p' "$GAME_ROOT/release/ReadMe" | head -1)"
  [ -n "$version" ] || die "no version in release/ReadMe"
  archive="$dist/WingCommander-$version.lha"
  if [ -e "$archive" ] && [ "${FORCE:-0}" != 1 ]; then die "$archive exists (FORCE=1 replaces it)"; fi
  stage="$GAME_ROOT/tmp/dist/package"
  rm -rf "$GAME_ROOT/tmp/dist"
  mkdir -p "$GAME_ROOT/tmp/dist" "$dist"
  (cd "$GAME_ROOT" && python3 tools/release_install.py --cd32 tmp/build/release/WingCommanderCD32 \
    --ocs tmp/build/release/WingCommander --output tmp/dist/package) > "$GAME_ROOT/tmp/dist/package.log" 2>&1 ||
    { cat "$GAME_ROOT/tmp/dist/package.log" >&2; die "release staging failed (tmp/dist/package.log)"; }
  rm -f "$archive"
  (cd "$stage" && "$LHA" a1o5q2 "$archive" WingCommanderHD.info WingCommanderHD) ||
    die "LHa failed for $archive"
  # The archive must hold exactly the staged files.
  python3 -I - "$LHA" "$archive" "$GAME_ROOT/tmp/dist/package-package-check.json" "$GAME_ROOT/tmp/dist" <<'PY' ||
import hashlib, json, subprocess, sys, tempfile
from pathlib import Path
lha, archive, report, scratch = sys.argv[1:]
expected = json.loads(Path(report).read_text())['files']
with tempfile.TemporaryDirectory(dir=scratch) as out:
    subprocess.run([lha, 'xqw=' + out, archive], check=True)
    got = {str(f.relative_to(out)): hashlib.sha256(f.read_bytes()).hexdigest()
           for f in sorted(Path(out).rglob('*')) if f.is_file()}
if got != expected:
    raise SystemExit('the archive differs from the staged files')
print(f'{archive}: {len(got)} files verified against the staging report')
PY
    { rm -f "$archive"; die "$archive failed its check"; }
}

# The quick unit tests: the reconstructions still give the original slaves, and the
# release slaves pass their native option, conversion and installer checks. The
# emulator-driven checks are run by hand (docs/development.md).
game_check() {
  local out="$GAME_ROOT/tmp/check"
  rm -rf "$out"
  mkdir -p "$out"
  (cd "$GAME_ROOT" &&
    for v in $VARIANTS; do
      env -u GAME_DIR -u SLAVE_FILE -u SOURCE VARIANT="$v" "$COMMON/build.sh" reconstruct > /dev/null
    done &&
    python3 tools/release_check.py tmp/build/release/WingCommanderCD32 --output tmp/check/release-cd32.json &&
    python3 tools/ocs_options_check.py tmp/build/release/WingCommander --output tmp/check/options-ocs &&
    python3 tools/release_install.py --cd32 tmp/build/release/WingCommanderCD32 \
      --ocs tmp/build/release/WingCommander --output tmp/check/package > /dev/null &&
    echo "WingCommander: reconstructions identical; release option, conversion and installer checks pass")
}
