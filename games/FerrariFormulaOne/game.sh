# Ferrari Formula One: the build (tools/build.py) and the harness's launch modes (tools/run.sh).

# tools/build.py assembles the host and its payloads and binds them through SPS 0481's
# relocation records, read from the installed racemenu (never copied into the slave).
game_build() {
  local build="$1" out="$2" game stage
  case "$build" in
    release) ;;
    *) die "no $build build of $VARIANT (game.sh game_build: release)" ;;
  esac
  game="$GAME_ROOT/tmp/game/$GAME_DIR/data/racemenu"
  [ -f "$game" ] || die "no tmp/game/$GAME_DIR/data/racemenu: run make unpack ARCHIVES=<directory> first"
  stage="$out/$VARIANT.d"
  rm -rf "$stage" "$out/$VARIANT.Slave"
  if ! (cd "$GAME_ROOT" && FF1_FINE_DEFINES= python3 tools/build.py --game "$game" --out "$stage") \
      > "$out/$VARIANT.log" 2>&1; then
    cat "$out/$VARIANT.log" >&2
    die "the $build build of $VARIANT failed (tmp/build/$build/$VARIANT.log)"
  fi
  cp "$stage/FerrariFormulaOne.slave" "$out/$VARIANT.Slave"
  (cd "$GAME_ROOT" && find src -type f | LC_ALL=C sort) > "$out/$VARIANT.deps"
}

# FF1_LAUNCH selects one of the harness's launch modes:
#   stdio       WHDLoad's output to DH1:startup-output.log, its result to DH0:whdload-exit.txt
#   diagnostic  without NOREQ, so WHDLoad's requesters stay up
#   session     RELEASE_SEASON_SOURCE (a season save) installed as DH1:data/qual.ses
game_prepare() {
  case "${FF1_LAUNCH:-}" in
    '') ;;
    stdio) WHD_ARGS="${WHD_ARGS:-} >DH1:startup-output.log"; VERIFY_EXIT=1 ;;
    diagnostic) WHD_DEFAULTS="PRELOAD SPLASHDELAY=0" ;;
    session) [ -f "${RELEASE_SEASON_SOURCE:-}" ] || die "FF1_LAUNCH=session needs RELEASE_SEASON_SOURCE" ;;
    *) die "FF1_LAUNCH is stdio, diagnostic or session" ;;
  esac
}

game_drives() {
  if [ "${FF1_LAUNCH:-}" = session ]; then cp "$RELEASE_SEASON_SOURCE" "$2/data/qual.ses"; fi
  [ "${FF1_HARNESS:-0}" = 1 ] || return 0
  # The launch record the captures copy into their results (tools/run.sh).
  RUN_SLAVE_PATH="${RUN_SLAVE:-$GAME_ROOT/tmp/game/$GAME_DIR/$SLAVE_FILE}" python3 - "$FSUAE_RUN" <<'PY'
import hashlib, json, os, pathlib, sys
keys = ('SLAVE', 'CPU', 'AMIGA_MODEL', 'CHIP_KB', 'SLOW_KB', 'FAST_KB', 'WHD_ARGS', 'WARP', 'FSUAE',
        'KICKSTART', 'WHDLOAD_BINARY', 'JOY0', 'JOY1', 'DETERMINISTIC', 'WINDOW', 'SOUND', 'NTSC')
m = {k: os.environ.get(k, '') for k in keys}
m['slave_sha256'] = hashlib.sha256(pathlib.Path(os.environ['RUN_SLAVE_PATH']).read_bytes()).hexdigest()
(pathlib.Path(sys.argv[1]) / 'launch.json').write_text(json.dumps(m, indent=2) + '\n')
PY
}
