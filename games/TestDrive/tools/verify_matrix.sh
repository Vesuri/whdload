#!/bin/bash
set -euo pipefail
. "$(dirname "$0")/env.sh"
cd "$HARNESS_ROOT"
python3 tools/verify_capture.py final-straight-a500 --fields 1300
python3 tools/verify_capture.py final-straight-a1200 --preset a1200 --fields 1300
python3 tools/verify_capture.py final-slow-a500 --c4 1 --fields 1300
python3 tools/verify_capture.py final-slow-a1200 --preset a1200 --c4 1 --fields 1300
python3 tools/verify_capture.py final-events-a500 --c1 2 --c5 23 --fields 1800
python3 tools/verify_capture.py final-events-a1200 --preset a1200 --c1 2 --c5 23 --fields 1800
python3 tools/verify_capture.py final-crash-block --c5 19 --fields 800
python3 tools/verify_capture.py final-demo-a500 --c5 0 --fields 1400
python3 tools/verify_capture.py final-demo-a1200 --preset a1200 --c5 0 --fields 1400
python3 tools/verify_capture.py final-disabled --c3 0 --c5 0 --fields 2
python3 tools/verify_capture.py final-route-a500 --c5 1 --fields 1300
python3 tools/verify_capture.py final-route-slow-a500 --c5 1 --c4 1 --fields 1300
python3 tools/verify_reload.py
python3 tools/check_phase7.py > tmp/phase7/acceptance.json
python3 tools/check_verify_tools.py > tmp/phase7/checker-negative-controls.json
