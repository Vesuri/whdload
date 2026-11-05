# 4D Sports Driving hooks (common/template/game.sh lists them).

# Both Amiga archives hold a 4DSportsDriving drawer, so each is unpacked into a drawer named
# after it: tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving is the installed SPS 1461
# game that runs, tmp/game/4DSportsDriving/4DSportsDrivingInstall the installer package.
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

# What the harness's own launcher did beyond common/run.sh, once the drives and the
# startup-sequence exist (game_setup runs from fsuae_options and again at the launch):
#   NTSC=1           Workbench 2.04 has no standalone monitor drivers: AddMonitor ntsc.monitor
#   P6_QUIT_MARKER=1 write DH1:quit-ok.txt ("P6_QUIT_OK") after WHDLoad returns
#   P3_HDF_BOOT=1    boot native IDE hard-disk images of the drives (tools/p3_hdf_boot.py,
#                    needs xdftool) instead of directory drives
game_setup() {
  [ -z "${GAME_SETUP_DONE:-}" ] || { FSUAE_SETUP_ARGS+=(${GAME_SETUP_DRIVES[@]+"${GAME_SETUP_DRIVES[@]}"}); return 0; }
  GAME_SETUP_DONE=1
  GAME_SETUP_DRIVES=()
  local seq="$DH0/s/startup-sequence"
  if [ "${NTSC:-0}" = 1 ] && [ "${WB:-1}" = 1 ]; then
    sed -i '' 's/^Stack 16384$/DF0:System\/AddMonitor 1 ntsc.monitor\
Stack 16384/' "$seq"
  fi
  if [ "${P6_QUIT_MARKER:-0}" = 1 ]; then
    printf '%s\n' 'Echo "P6_QUIT_OK" >DH1:quit-ok.txt' >> "$seq"
  fi
  if [ "${P3_HDF_BOOT:-0}" = 1 ]; then
    python3 "$GAME_ROOT/tools/p3_hdf_boot.py" "$FSUAE_RUN"
    # The setup arguments come before common/run.sh's directory drives, and the first
    # value of an option wins.
    GAME_SETUP_DRIVES=(--hard_drive_0="$FSUAE_RUN/dh0.hdf" --hard_drive_0_priority=10
      --hard_drive_0_controller=ide0 --hard_drive_1="$FSUAE_RUN/dh1.hdf"
      --hard_drive_1_controller=ide1)
  fi
  FSUAE_SETUP_ARGS+=(${GAME_SETUP_DRIVES[@]+"${GAME_SETUP_DRIVES[@]}"})
}

# The static hook audit (tools/hook_audit.py): every declared hook range covers whole
# instructions of the original program and no relocation or PC-relative branch enters one.
# It reads the installed program, so it runs once make unpack has installed the drawer.
# The emulator-driven checks are run by hand (docs/open-work.md, docs/smooth-play-plan.md).
game_check() {
  (
    cd "$GAME_ROOT"
    if [ ! -f "tmp/game/$GAME_DIR/data/stunts" ]; then
      echo "skipped (no installed drawer; make unpack): tools/hook_audit.py"; exit 0
    fi
    python3 tools/hook_audit.py > tmp/check-hook_audit.log 2>&1 ||
      { cat tmp/check-hook_audit.log >&2; die "tools/hook_audit.py failed (tmp/check-hook_audit.log)"; }
    echo "passed: tools/hook_audit.py"
  )
}
