#!/usr/bin/env bash
# Sequential original/reconstruction pairs; state waits are in boot_gate.py.
set -euo pipefail
cd "$(dirname "$0")/.."
. amiga/env.sh
: "${FSUAE:?Set FSUAE to an emulator supporting the native key-raw-v1 route}"
OUT=$1 LAYOUT=$2 CONTROL=$3
case "$CONTROL" in /*) ;; *) CONTROL="$PWD/$CONTROL" ;; esac
python3 - "$OUT" <<'PY'
from pathlib import Path
import sys
out=Path(sys.argv[1]).resolve(); root=Path.cwd()
if (root/'tmp').resolve() not in out.parents or out.exists():
    raise SystemExit('choose a new A/B directory below tmp/')
out.mkdir(parents=True)
PY
for custom in 0 1 2 3; do
  for build in original reconstructed; do
    slave=""; [ "$build" != reconstructed ] || slave="$CONTROL"
    echo "Custom5=$custom $build: boot through simulator to name prompt"
    SLAVE="$slave" WHD_ARGS="CUSTOM5=$custom" python3 tools/boot_gate.py \
      --simulator --layout "$LAYOUT" --output "$OUT/$build-$custom" \
      > "$OUT/$build-$custom.log" 2>&1
  done
  python3 tools/compare_boots.py "$OUT/original-$custom" "$OUT/reconstructed-$custom" \
    > "$OUT/menu-$custom.json"
  python3 tools/compare_boots.py --name "$OUT/original-$custom" "$OUT/reconstructed-$custom" \
    > "$OUT/name-$custom.json"
  echo "Custom5=$custom: exact menu and name-prompt state/picture matches"
done
