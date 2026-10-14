#!/usr/bin/env bash
# Adapted from Legends of Valour; each boot gets fresh drives, never deletes a tree.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -n "${SLAVE:-}" ]; then SLAVE="$(cd "$(dirname "$SLAVE")" && pwd)/$(basename "$SLAVE")"; export SLAVE; fi
cd "$ROOT/amiga"
. ./env.sh
export WC_VARIANT="${WC_VARIANT:-cd32}"
case "$WC_VARIANT" in
  cd32) GAME_DIR=WingCommanderCD32; default_setup=a1200-fast ;;
  ocs) GAME_DIR=WingCommander; default_setup=a500 ;;
  *) echo "WC_VARIANT must be cd32 or ocs" >&2; exit 1 ;;
esac
export AMIGA_SETUP="${AMIGA_SETUP:-$default_setup}"
# The pinned core takes CHIP write attributes from the wrong MMU cache entry.
# Build locally; never modify the shared emulator or override an explicit choice.
if [ -z "${FSUAE:-}" ] && [ "${1:-}" != stop ]; then
  case "$AMIGA_SETUP" in
    a1200-040|a1200-060)
      python3 "$ROOT/tools/build_mmu_fix.py" --ensure
      FSUAE="$ROOT/tmp/fsuae-mmu-fixed/fs-uae"
      ;;
  esac
fi
export FSUAE="${FSUAE:-$FSUAE_ARM}"
FSUAE_RUN="${FSUAE_RUN:-../tmp/run}"
# The shared launcher expects a path relative to amiga/. Canonicalise overrides
# before it constructs its pid/log paths, and reject symlink escapes from tmp/.
FSUAE_RUN="$(python3 - "$ROOT" "$FSUAE_RUN" <<'PYRUN'
from pathlib import Path
import os, sys
root, run = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
if (root/'tmp').resolve() not in run.parents:
    raise SystemExit('FSUAE_RUN must be below this project tmp/')
print(os.path.relpath(run, Path.cwd()))
PYRUN
)"
export FSUAE_RUN
. "$FSUAE_COMMON"
# A pidfile alone is insufficient if a PID was reused by another project's UAE.
if [ -f "$FSUAE_PIDFILE" ]; then
  tracked=$(cat "$FSUAE_PIDFILE")
  if fsuae_is_a "$tracked" fs-uae && ! fsuae_is_ours "$tracked"; then
    echo "recorded emulator belongs to another directory; refusing to stop it" >&2
    exit 1
  fi
fi
case "${1:-}" in stop) fsuae_stop_previous; exit ;; esac
FSUAE_CLAIM_STRICT=1
fsuae_prepare
mkdir -p "$FSUAE_RUN"
BOOT=$(mktemp -d "$FSUAE_RUN/boot.XXXXXX")
python3 "$ROOT/tools/runtime_inputs.py" "$BOOT"
DH0="$BOOT/dh0"; DH1="$BOOT/dh1/$GAME_DIR"
chmod -R u+w "$DH0" "$DH1"
printf 'Expert\nReadDelay=0\n' > "$DH0/s/WHDLoad.prefs"
printf '%s\n' 'DF0:C/Assign C: DF0:C' 'DF0:C/Assign LIBS: DF0:Libs' 'DF0:C/Assign DEVS: DH0:devs' \
  'Stack 16384' 'FailAt 999' 'CD DH1:' \
  "WHDLoad $GAME_DIR.Slave PRELOAD SPLASHDELAY=0 NOREQ ${WHD_ARGS:-}" > "$DH0/s/startup-sequence"
mkdir -p "$BOOT/state" "$BOOT/shots"
export FSEMU_SCREENSHOTS_DIR="$PWD/$BOOT/shots"
JOY0="${JOY0:-mouse}" JOY1="${JOY1:-keyboard}"
# The launcher rebuilds its preset at launch, so wrap that preset function.
# Numeric frequency overflows in the pinned core; stock 020 uses multiplier 4.
if [ "${INTRO_STOCK_CLOCK:-0}" = 1 ]; then
  setup_function=$(declare -f fsuae_setup)
  eval "${setup_function/fsuae_setup/wc_base_setup}"
  fsuae_setup() {
    wc_base_setup || return 1
    [ "$AMIGA_SETUP" = a1200-fast ] || { echo "intro clock requires a1200-fast" >&2; return 1; }
    local i
    for i in "${!FSUAE_SETUP_ARGS[@]}"; do
      case "${FSUAE_SETUP_ARGS[$i]}" in
        --uae_cpu_multiplier=*) FSUAE_SETUP_ARGS[$i]=--uae_cpu_multiplier=4 ;;
        --uae_cpu_frequency=*) FSUAE_SETUP_ARGS[$i]=--uae_cpu_frequency=0 ;;
      esac
    done
  }
fi
# Timing-core selection is independent of WHDLoad's NoMMU tooltype.
if [ "${WC_NOMMU_CORE:-0}" = 1 ]; then
  setup_function=$(declare -f fsuae_setup)
  eval "${setup_function/fsuae_setup/wc_mmu_base_setup}"
  fsuae_setup() {
    wc_mmu_base_setup || return 1
    case "$AMIGA_SETUP" in
      a1200-030) CPU=68EC030 ;;
      a1200-040) CPU=68040-NOMMU ;;
      a1200-060) CPU=68060-NOMMU ;;
      *) echo "NOMMU timing core requires an accelerated preset" >&2; return 1 ;;
    esac
    local i
    for i in "${!FSUAE_SETUP_ARGS[@]}"; do
      case "${FSUAE_SETUP_ARGS[$i]}" in
        --cpu=*) FSUAE_SETUP_ARGS[$i]=--cpu="$CPU" ;;
        --uae_mmu_model=*) FSUAE_SETUP_ARGS[$i]=--uae_mmu_model=0 ;;
        --uae_cpu_cycle_exact=*|--uae_cpu_memory_cycle_exact=*|--uae_blitter_cycle_exact=*)
          FSUAE_SETUP_ARGS[$i]="${FSUAE_SETUP_ARGS[$i]%%=*}=true" ;;
      esac
    done
  }
fi
# Diagnostic compatibility with the established 030 measurement baseline.
# New shared presets enable data caching plus an indirect UAE board which the
# retained observer build does not boot. Preserve shipping/default setup unless
# this explicitly selected capture requests the prior model.
if [ "${WC_BASELINE_CACHE_MODEL:-0}" = 1 ]; then
  setup_function=$(declare -f fsuae_setup)
  eval "${setup_function/fsuae_setup/wc_cache_base_setup}"
  fsuae_setup() {
    wc_cache_base_setup || return 1
    case "$AMIGA_SETUP" in a1200-030|a1200-040|a1200-060) ;; *) echo "baseline cache model requires an accelerated preset" >&2; return 1 ;; esac
    local arg
    local baseline_args=()
    for arg in "${FSUAE_SETUP_ARGS[@]}"; do
      case "$arg" in
        --uae_cpu_data_cache=*) baseline_args+=(--uae_cpu_data_cache=false) ;;
        --uae_uaeboard=full+indirect) ;;
        *) baseline_args+=("$arg") ;;
      esac
    done
    FSUAE_SETUP_ARGS=("${baseline_args[@]}")
  }
fi
# Diagnostic CPU-speed bracket: "max" runs the non-cycle-exact CPU as fast as
# the host allows against unchanged emulated chipset timing.
if [ -n "${WC_CPU_SPEED:-}" ]; then
  case "$WC_CPU_SPEED" in real|max) ;; *) echo "WC_CPU_SPEED must be real or max" >&2; exit 1 ;; esac
  setup_function=$(declare -f fsuae_setup)
  eval "${setup_function/fsuae_setup/wc_speed_base_setup}"
  fsuae_setup() {
    wc_speed_base_setup || return 1
    local i
    for i in "${!FSUAE_SETUP_ARGS[@]}"; do
      case "${FSUAE_SETUP_ARGS[$i]}" in
        --uae_cpu_cycle_exact=true) echo "WC_CPU_SPEED requires a non-cycle-exact preset" >&2; return 1 ;;
        --uae_cpu_speed=*) FSUAE_SETUP_ARGS[$i]=--uae_cpu_speed="$WC_CPU_SPEED" ;;
      esac
    done
  }
fi
# Set the ceiling intervention explicitly, including the normal control value.
setup_function=$(declare -f fsuae_setup)
eval "${setup_function/fsuae_setup/wc_blitter_base_setup}"
fsuae_setup() {
  wc_blitter_base_setup || return 1
  local immediate=false i found=0
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
  if [ "$found" = 0 ]; then FSUAE_SETUP_ARGS+=(--uae_immediate_blits="$immediate"); fi
}
# Native OCS baseline uses true Zorro-II Fast RAM, without trapdoor slow RAM.
if [ "$WC_VARIANT" = ocs ] && [ "$AMIGA_SETUP" = a500 ]; then
  setup_function=$(declare -f fsuae_setup)
  eval "${setup_function/fsuae_setup/wc_ocs_base_setup}"
  fsuae_setup() {
    wc_ocs_base_setup || return 1
    local i
    FAST_KB=4096 SLOW_KB=0
    for i in "${!FSUAE_SETUP_ARGS[@]}"; do
      case "${FSUAE_SETUP_ARGS[$i]}" in
        --fast_memory=*) FSUAE_SETUP_ARGS[$i]=--fast_memory=4096 ;;
        --slow_memory=*) FSUAE_SETUP_ARGS[$i]=--slow_memory=0 ;;
      esac
    done
  }
fi
fsuae_options
fsuae_launch --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  --floppy_drive_0="$WORKBENCH_ADF" --state_dir="$BOOT/state"
