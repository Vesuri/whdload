#!/usr/bin/env bash
# Build the slave with the harness's fixtures, selected by environment variables
# (VERIFY=1, SIM_A4000=1, SIM_MANUAL=1, ...: docs/smooth-play-plan.md), for the tools and docs
# that name tmp/build/4DSportsDriving[-verify|-manual|-live-test|-raster-test].slave:
#   VERIFY=1 SIM_A4000=1 tools/build.sh
# The build is common/build.sh's (make build BUILD=NAME VASM_EXTRA='...') in tmp/build/NAME/,
# NAME being tool_ and the suffix, copied to tmp/build/4DSportsDriving<suffix>.slave with its
# listing beside it. Without variables it is the release build (make slave). The plain
# VERIFY=1 and SIM_MANUAL=1 builds equal make verify and make build BUILD=manual.
set -euo pipefail
GAME_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$GAME_ROOT/tmp/build"
if [ "${SIM_MANUAL:-0}" = 1 ]; then
  VERIFY=1; SIM_A4000=1; SIM_MODE_MENU=1
fi
if [ "${SIM_A4000:-0}" = 1 ]; then
  [ "${VERIFY:-0}" = 1 ] || { echo "SIM_A4000 requires VERIFY=1" >&2; exit 1; }
  SIM_PROBE=1; SIM_FIXTURE=1; SIM_SCHEDULE=1; SIM_PHYSICS=1
  if [ "${SIM_A4000_NATIVE:-0}" = 1 ]; then TAPE_SIMULATION="${TAPE_SIMULATION:-20}"; else TAPE_SIMULATION=20; fi
fi
if [ "${SIM_MODE_MENU:-0}" = 1 ]; then
  [ "${SIM_A4000:-0}" = 1 ] || { echo "SIM_MODE_MENU requires SIM_A4000=1" >&2; exit 1; }
  SIM_A4000_NATIVE=1; TAPE_SIMULATION="${SIM_MENU_RATE:-50}"
fi
if [ "${SIM_MANUAL:-0}" = 1 ] || [ "${SIM_LIVE_DRIVE:-0}" = 1 ]; then SIM_FIXTURE=0; fi
if [ "${SIM_REPLAY_IO_TEST:-0}" = 1 ]; then SIM_REPLAY_FILE_TEST=1; fi
if [ "${SIM_RUNTIME:-0}" = 1 ] && [ "${VERIFY:-0}" = 1 ]; then echo "SIM_RUNTIME excludes VERIFY" >&2; exit 1; fi
DEFINES=(); SUFFIX=""
if [ "${SIM_RUNTIME:-0}" = 1 ]; then DEFINES+=(-DSIM_RUNTIME=1); fi
if [ "${VERIFY:-0}" = 1 ]; then DEFINES=(-DVERIFY=1 -DTAPE_SIMULATION="${TAPE_SIMULATION:-10}" -DTAPE_DETAIL="${TAPE_DETAIL:-0}" -DTAPE_FIRST="${TAPE_FIRST:-25}" -DTAPE_GAP="${TAPE_GAP:-25}" -DTAPE_KEYS="${TAPE_KEYS:-200}"); SUFFIX="-verify"; fi
if [ "${SIM_FIXTURE_IDLE:-0}" = 1 ]; then DEFINES+=(-DSIM_FIXTURE_IDLE=1); fi
if [ -n "${SIM_FIXTURE_YAW_FRACTION:-}" ]; then DEFINES+=(-DSIM_FIXTURE_YAW_FRACTION="$SIM_FIXTURE_YAW_FRACTION"); fi
if [ -n "${SIM_STARTUP_TESTS:-}" ]; then DEFINES+=(-DSIM_STARTUP_TESTS="$SIM_STARTUP_TESTS"); fi
if [ "${SIM_LIVE_DRIVE:-0}" = 1 ]; then DEFINES+=(-DSIM_LIVE_DRIVE=1 -DTAPE_ACCEL=1); fi
if [ "${SIM_AUX_SPAWN_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_AUX_SPAWN_TEST=1); fi
if [ "${SIM_CAMERA_SEED_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_CAMERA_SEED_TEST=1); fi
if [ "${SIM_CAMERA_NATIVE_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_CAMERA_NATIVE_TEST=1); fi
if [ "${SIM_AUX_NATIVE_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_AUX_NATIVE_TEST=1); fi
if [ "${SIM_REPLAY_LOAD_ERROR_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_REPLAY_LOAD_ERROR_TEST=1); fi
if [ "${SIM_REPLAY_SAVE_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_REPLAY_SAVE_TEST=1 -DSIM_REPLAY_SAVE_RATE="${SIM_MENU_RATE:-50}" -DSIM_REPLAY_SAVE_TICK="${SIM_REPLAY_SAVE_TICK:-160}"); fi
if [ -n "${SIM_REPLAY_LEGACY_TEST:-}" ]; then DEFINES+=(-DSIM_REPLAY_LEGACY_TEST="$SIM_REPLAY_LEGACY_TEST"); fi
if [ "${SIM_REPLAY_MENU:-0}" = 1 ]; then DEFINES+=(-DSIM_REPLAY_MENU=1); fi
if [ "${SIM_MANUAL:-0}" = 1 ]; then DEFINES+=(-DSIM_MANUAL=1); SUFFIX="-manual"; fi
if [ "${SIM_LIVE_INPUT_TEST:-0}" = 1 ]; then
  [ "${SIM_MANUAL:-0}" = 1 ] || { echo "SIM_LIVE_INPUT_TEST requires SIM_MANUAL=1" >&2; exit 1; }
  DEFINES+=(-DSIM_LIVE_INPUT_TEST=1); SUFFIX="-live-test"
fi
if [ "${VERIFY:-0}" = 1 ] && [ "${ACCEL:-0}" = 1 ]; then DEFINES+=(-DTAPE_ACCEL=1); fi
if [ -n "${PERF_MASK:-}" ]; then DEFINES+=(-DPERF_MASK="$PERF_MASK"); fi
if [ "${P3_QUAD:-0}" = 1 ]; then DEFINES+=(-DP3_QUAD=1); fi
if [ "${P3_BAND:-0}" = 1 ]; then DEFINES+=(-DP3_BAND=1); fi
if [ "${P3_FRAME:-0}" = 1 ]; then P3_RASTER=1; P3_DIRECT=1; DEFINES+=(-DP3_FRAME=1); fi
if [ "${P3_FRAME_TWIN:-0}" = 1 ]; then [ "${VERIFY:-0}" = 1 ] || exit 1; DEFINES+=(-DP3_FRAME_TWIN=1); fi
if [ "${P3_RASTER:-0}" = 1 ]; then
  if [ "${P3_DIRECT:-0}" = 1 ]; then DEFINES+=(-DP3_DIRECT=1); SUFFIX="-raster-test";
  else [ "${VERIFY:-0}" = 1 ] || exit 1; fi
  DEFINES+=(-DP3_RASTER=1)
fi
if [ "${VERIFY:-0}" = 1 ] && [ "${TWIN:-0}" = 1 ]; then DEFINES+=(-DPERF_TWIN=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${PIXELS:-0}" = 1 ]; then DEFINES+=(-DTAPE_PIXELS=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${TAPE_SCENARIO:-}" ]; then DEFINES+=(-DTAPE_SCENARIO="$TAPE_SCENARIO"); fi
if [ "${VERIFY:-0}" = 1 ] && { [ "${SIM_PROBE:-0}" = 1 ] || [ "${SIM_FIXTURE:-0}" = 1 ] || [ "${SIM_SCHEDULE:-0}" = 1 ]; }; then DEFINES+=(-DSIM_PROBE=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_FIXTURE:-0}" = 1 ]; then DEFINES+=(-DSIM_FIXTURE=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_SCHEDULE:-0}" = 1 ]; then DEFINES+=(-DSIM_SCHEDULE=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_PHYSICS:-0}" = 1 ]; then DEFINES+=(-DSIM_PHYSICS=1); fi
if [ "${SIM_TRACE:-0}" = 1 ]; then DEFINES+=(-DSIM_TRACE=1); fi
if [ "${SIM_INPUT_EDGE_STEERING:-0}" = 1 ]; then
  [ "${SIM_INPUT_EDGE_TEST:-0}" = 1 ] || { echo "SIM_INPUT_EDGE_STEERING requires SIM_INPUT_EDGE_TEST=1" >&2; exit 1; }
  DEFINES+=(-DSIM_INPUT_EDGE_STEERING=1)
fi
if [ "${SIM_INPUT_EDGE_TEST:-0}" = 1 ]; then
  [ "${VERIFY:-0}" = 1 ] && [ "${SIM_LIVE_DRIVE:-0}" = 1 ] || { echo "SIM_INPUT_EDGE_TEST requires VERIFY=1 SIM_LIVE_DRIVE=1" >&2; exit 1; }
  DEFINES+=(-DSIM_INPUT_EDGE_TEST=1)
fi
if [ "${SIM_A4000:-0}" = 1 ]; then DEFINES+=(-DSIM_A4000=1); fi
if [ -n "${SIM_REPLAY_CLOCK_SPEED:-}" ]; then DEFINES+=(-DSIM_REPLAY_CLOCK_SPEED="$SIM_REPLAY_CLOCK_SPEED"); fi
if [ "${SIM_REPLAY_RELOAD_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_REPLAY_RELOAD_TEST=1 -DSIM_REPLAY_RELOAD_TARGET="${SIM_REPLAY_RELOAD_TARGET:-1555}"); fi
if [ "${SIM_REPLAY_IO_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_REPLAY_IO_TEST=1); fi
if [ "${SIM_REPLAY_FILE_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_REPLAY_FILE_TEST=1 -DSIM_REPLAY_FILE_TICK="${SIM_REPLAY_FILE_TICK:-155}"); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_SCORE_INSERT_TEST:-}" ]; then DEFINES+=(-DSIM_SCORE_INSERT_TEST="$SIM_SCORE_INSERT_TEST"); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_SCORE_DISPLAY_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_SCORE_DISPLAY_TEST=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_SCORE_AUTOCREATE_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_SCORE_AUTOCREATE_TEST=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_SCORE_LOAD_TICK:-}" ]; then DEFINES+=(-DSIM_SCORE_LOAD_TICK="$SIM_SCORE_LOAD_TICK"); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_SCORE_LOAD_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_SCORE_LOAD_TEST=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_SCORE_RESET_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_SCORE_RESET_TEST=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_SCORE_IO_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_SCORE_IO_TEST=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_EVENTS_NATIVE_TEST:-}" ]; then DEFINES+=(-DSIM_EVENTS_NATIVE_TEST="$SIM_EVENTS_NATIVE_TEST"); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_RESULTS_DISPLAY_TEST:-}" ]; then DEFINES+=(-DSIM_RESULTS_DISPLAY_TEST="$SIM_RESULTS_DISPLAY_TEST"); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_TIME_DISPLAY_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_TIME_DISPLAY_TEST=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_HISTORY_ROTATION_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_HISTORY_ROTATION_TEST=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_HISTORY_ROTATION_BASE:-}" ]; then DEFINES+=(-DSIM_HISTORY_ROTATION_BASE="$SIM_HISTORY_ROTATION_BASE"); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_HISTORY_END_SEEK_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_HISTORY_END_SEEK_TEST=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_CAPACITY_FIXTURE:-0}" = 1 ]; then DEFINES+=(-DSIM_CAPACITY_FIXTURE=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_HISTORY_SEEK_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_HISTORY_SEEK_TEST=1 -DSIM_HISTORY_SEEK_TARGET="${SIM_HISTORY_SEEK_TARGET:-55}"); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_HISTORY_TEST_SPACING:-}" ]; then DEFINES+=(-DSIM_HISTORY_TEST_SPACING="$SIM_HISTORY_TEST_SPACING"); fi
if [ "${SIM_A4000_NATIVE:-0}" = 1 ]; then DEFINES+=(-DSIM_A4000_NATIVE=1); fi
if [ "${SIM_MODE_MENU:-0}" = 1 ]; then DEFINES+=(-DSIM_MODE_MENU=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_FIXTURE_LONGITUDINAL:-0}" = 1 ]; then DEFINES+=(-DSIM_FIXTURE_LONGITUDINAL=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_FIXTURE_THROTTLE_SECONDS:-}" ]; then DEFINES+=(-DSIM_FIXTURE_THROTTLE_SECONDS="$SIM_FIXTURE_THROTTLE_SECONDS"); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_FIXTURE_GEARS:-0}" = 1 ]; then DEFINES+=(-DSIM_FIXTURE_GEARS=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_FIXTURE_SAMPLES:-}" ]; then DEFINES+=(-DSIM_FIXTURE_SAMPLES="$SIM_FIXTURE_SAMPLES"); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_FIXTURE_SAMPLE_HZ:-}" ]; then DEFINES+=(-DSIM_FIXTURE_SAMPLE_HZ="$SIM_FIXTURE_SAMPLE_HZ"); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_FIXTURE_OPPONENT_BRAKE:-0}" = 1 ]; then DEFINES+=(-DSIM_FIXTURE_OPPONENT_BRAKE=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_FIXTURE_OPPONENT_SPIN:-}" ]; then DEFINES+=(-DSIM_FIXTURE_OPPONENT_SPIN="$SIM_FIXTURE_OPPONENT_SPIN"); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_FIXTURE_OPPONENT_SLIP:-}" ]; then DEFINES+=(-DSIM_FIXTURE_OPPONENT_SLIP="$SIM_FIXTURE_OPPONENT_SLIP"); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_FIXTURE_HEADING:-}" ]; then DEFINES+=(-DSIM_FIXTURE_HEADING="$SIM_FIXTURE_HEADING"); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_MODAL_FIXTURE:-0}" = 1 ]; then DEFINES+=(-DSIM_MODAL_FIXTURE=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_RESTART_FIXTURE:-0}" = 1 ]; then DEFINES+=(-DSIM_RESTART_FIXTURE=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_CONTACT_PROBE:-0}" = 1 ]; then DEFINES+=(-DSIM_CONTACT_PROBE=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_TILT_COLLECT_VERIFY:-0}" = 1 ]; then DEFINES+=(-DSIM_TILT_COLLECT_VERIFY=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_FIXTURE_CONTACT_RAMP:-0}" = 1 ]; then DEFINES+=(-DSIM_FIXTURE_CONTACT_RAMP=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_FIXTURE_INVERTED:-0}" = 1 ]; then DEFINES+=(-DSIM_FIXTURE_INVERTED=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_FIXTURE_INVERTED_Y:-}" ]; then DEFINES+=(-DSIM_FIXTURE_INVERTED_Y="$SIM_FIXTURE_INVERTED_Y"); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_FIXTURE_INVERTED_SCALE_TEST:-0}" = 1 ]; then DEFINES+=(-DSIM_FIXTURE_INVERTED_SCALE_TEST=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_FIXTURE_DROP:-0}" = 1 ]; then DEFINES+=(-DSIM_FIXTURE_DROP=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_FIXTURE_SUSPENSION:-0}" = 1 ]; then DEFINES+=(-DSIM_FIXTURE_SUSPENSION=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_FIXTURE_OFFROAD:-0}" = 1 ]; then DEFINES+=(-DSIM_FIXTURE_OFFROAD=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${SIM_FIXTURE_TURN_SECONDS:-}" ]; then DEFINES+=(-DSIM_FIXTURE_TURN_SECONDS="$SIM_FIXTURE_TURN_SECONDS"); fi
if [ "${VERIFY:-0}" = 1 ] && [ "${SIM_FIXTURE_RECOVERY:-0}" = 1 ]; then DEFINES+=(-DSIM_FIXTURE_RECOVERY=1); fi
if [ "${VERIFY:-0}" = 1 ] && [ -n "${TAPE_OPPONENT:-}" ]; then DEFINES+=(-DTAPE_OPPONENT="$TAPE_OPPONENT"); fi
if [ "${P3_SOLID:-0}" = 1 ]; then DEFINES+=(-DP3_SOLID=1); fi
if [ "${P3_BACKGROUND:-0}" = 1 ]; then DEFINES+=(-DP3_BACKGROUND=1); fi
if [ "${P3_PIPELINE:-0}" = 1 ]; then { [ "${SIM_A4000:-0}" = 1 ] || [ "${SIM_RUNTIME:-0}" = 1 ]; } && [ "${P3_BACKGROUND:-0}" = 1 ] || exit 1; DEFINES+=(-DP3_PIPELINE=1); fi
name="tool_$(printf '%s' "${SUFFIX#-}" | tr -c 'A-Za-z0-9_' '_')"
[ "$name" != tool_ ] || name=tool_release
VASM_EXTRA="${DEFINES[*]+${DEFINES[*]}} -L tmp/build/4DSportsDriving${SUFFIX}.lst" \
  VARIANT=4DSportsDriving GAME=4DSportsDriving "$GAME_ROOT/../../common/build.sh" "$name" > /dev/null
cp -f "$GAME_ROOT/tmp/build/$name/4DSportsDriving.Slave" "$GAME_ROOT/tmp/build/4DSportsDriving${SUFFIX}.slave"
echo "tmp/build/4DSportsDriving${SUFFIX}.slave"
