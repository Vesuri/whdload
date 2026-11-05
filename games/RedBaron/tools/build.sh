#!/usr/bin/env bash
# The harness build, for the tools that select a build through the environment:
#   tools/build.sh                 tmp/build/RedBaron.slave (the release build)
#   VERIFY=1 tools/build.sh        tmp/build/RedBaron-verify.slave, with the VERIFY_* options
#   DEVELOPER=1 tools/build.sh     tmp/build/RedBaron-developer.slave
# Each is common/build.sh's build named tool_release, tool_verify or tool_developer
# (tmp/build/<name>/RedBaron.Slave), copied to the old name, with its listing beside it
# (<output>.lst). `make slave|verify|developer` are the same builds without the options.
set -euo pipefail
GAME_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
defines=()
name=tool_release
output=RedBaron.slave
if [ "${VERIFY:-0}" = 1 ]; then
  defines=(-DVERIFY=1)
  if [ -n "${VERIFY_D5_SCENARIO:-}" ]; then defines+=("-DVERIFY_D5_SCENARIO=$VERIFY_D5_SCENARIO"); fi
  if [ "${VERIFY_WORLD_QUANTUM_TWIN:-0}" = 1 ]; then defines+=(-DVERIFY_WORLD_QUANTUM_TWIN=1); fi
  if [ "${VERIFY_BANK_CYCLE:-0}" = 1 ]; then defines+=(-DVERIFY_BANK_CYCLE=1); fi
  if [ -n "${VERIFY_SPAN_TWIN_FAULT:-}" ]; then defines+=("-DVERIFY_SPAN_TWIN_FAULT=$VERIFY_SPAN_TWIN_FAULT"); fi
  if [ "${VERIFY_FAST_FRAME_TWIN:-0}" = 1 ]; then defines+=(-DVERIFY_FAST_FRAME_TWIN=1); fi
  if [ -n "${VERIFY_FAST_FRAME_FAULT:-}" ]; then defines+=("-DVERIFY_FAST_FRAME_FAULT=$VERIFY_FAST_FRAME_FAULT"); fi
  if [ "${VERIFY_ALLOC_LOG:-0}" = 1 ]; then defines+=(-DVERIFY_ALLOC_LOG=1); fi
  if [ -n "${VERIFY_CACHE_PROBE_FLAGS:-}" ]; then defines+=("-DVERIFY_CACHE_PROBE_FLAGS=$VERIFY_CACHE_PROBE_FLAGS"); fi
  if [ -n "${VERIFY_CACHE_PROBE_RESULT:-}" ]; then defines+=("-DVERIFY_CACHE_PROBE_RESULT=$VERIFY_CACHE_PROBE_RESULT"); fi
  if [ "${PANEL_CHECK:-0}" = 1 ]; then defines+=(-DVERIFY_PANEL_CHECK=1); fi
  name=tool_verify
  output=RedBaron-verify.slave
elif [ "${DEVELOPER:-0}" = 1 ]; then
  defines=(-DDEVELOPER=1)
  name=tool_developer
  output=RedBaron-developer.slave
fi
mkdir -p "$GAME_ROOT/tmp/build"
VASM_EXTRA="${defines[*]+${defines[*]}} -L tmp/build/$output.lst" VARIANT=RedBaron GAME=RedBaron \
  "$GAME_ROOT/../../common/build.sh" "$name" > /dev/null
cp -f "$GAME_ROOT/tmp/build/$name/RedBaron.Slave" "$GAME_ROOT/tmp/build/$output"
