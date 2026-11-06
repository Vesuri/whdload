#!/bin/bash
# Boot one configuration, screenshot after $WAIT seconds, stop. usage: smoke_step1.sh LABEL [env...]
set -u
cd "$(dirname "$0")/.."
label=$1; shift
out=tmp/shots/step1; mkdir -p $out
env "$@" python3 tools/tfx.py serve > $out/serve-$label.log 2>&1 &
until grep -q -E 'serving on|Error|Traceback' $out/serve-$label.log; do sleep 1; done
python3 tools/tfx.py wait ${WAIT:-40} >/dev/null
python3 tools/tfx.py shot $out/$label.png | cut -c1-120
python3 tools/tfx.py quit >/dev/null
wait
