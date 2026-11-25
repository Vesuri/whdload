#!/bin/bash
# tools/boot.sh SHOT [WAIT_TITLE] [WAIT_GAME]: boot under the server (the run options come
# from the environment; INSTANCE is required), wait for the title menu, run the route to the
# first hole (PLAY_SCALE multiplies its waits), wait, save SHOT and stop the emulator. A test
# run, never the user's.
set -eu
cd "$(dirname "$0")/.."
. ../../common/env.sh
[ -n "${INSTANCE:-}" ] && [ "$INSTANCE" != default ] || { echo "boot.sh: set INSTANCE" >&2; exit 1; }
shot="$1"; wt="${2:-12}"; wg="${3:-20}"
mkdir -p tmp/run/"$INSTANCE"
log=tmp/run/"$INSTANCE"/serve.log
WARP="${WARP:-1}" WINDOW="${WINDOW:-none}" python3 tools/links.py serve > "$log" 2>&1 &
for i in $(seq 1 60); do grep -q "serving on" "$log" && break; sleep 1; done
grep -q "serving on" "$log" || { cat "$log"; exit 1; }
trap 'python3 tools/links.py quit >/dev/null 2>&1 || true' EXIT
python3 tools/links.py wait "$wt" >/dev/null
python3 tools/links.py play ${PLAY_SCALE:-1} >/dev/null
python3 tools/links.py wait "$wg" >/dev/null
# stop first: on the a1200-040 the MMU messages WHDLoad causes otherwise break the capture
python3 tools/links.py stop >/dev/null
python3 tools/links.py shot "$shot" | grep -o '^.* kind=[0-9]* [0-9]* bytes'
