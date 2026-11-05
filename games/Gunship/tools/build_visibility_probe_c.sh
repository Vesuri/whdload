#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/../../common/env.sh"
mkdir -p "$ROOT/tmp/c"
ROOT="$ROOT" python3 - <<'PY'
import os
from pathlib import Path
root=Path(os.environ['ROOT'])
s=(root/'src/GunshipHD.s').read_text()
s=s.replace('bsr timing_runtime_dispatch','bsr timing_runtime_dispatch\n bsr vp_dispatch_near')
s=s.replace('include "timing-slave.i"', '''vp_dispatch_near:
 move.l a3,-(sp)
.base:
 lea .base(pc),a3
 adda.l #visibility_probe_install-.base,a3
 jsr (a3)
 movea.l (sp)+,a3
 rts
 include "timing-slave.i"''')
v=(root/'src/verify.i').read_text().replace('verify_frames:', ' include "visibility_probe_c.i"\nverify_frames:')
(root/'tmp/c/verify-probe.i').write_text(v)
s=s.replace('include "verify.i"','include "verify-probe.i"')
(root/'tmp/c/visibility-probe.s').write_text(s)
PY
extra=(); output=visibility-probe
if [ "${VP_SABOTAGE:-0}" = 1 ]; then extra=(-DVP_SABOTAGE=1); output=visibility-sabotage; fi
if [ "${VP_TIMING:-0}" = 1 ]; then extra+=(-DVP_TIMING=1); output=visibility-timing; fi
if [ "${VP_OWNER:-0}" = 1 ]; then extra+=(-DVP_OWNER=1); output=visibility-owner; fi
if [ "${VP_RETAINED:-0}" = 1 ]; then extra+=(-DVP_OWNER=1 -DVP_RETAINED=1); output=visibility-retained; fi
if [ "${VP_PANEL:-0}" = 1 ]; then extra+=(-DVP_PANEL=1); output=target-panel; fi
if [ "${VP_PANEL_SABOTAGE:-0}" = 1 ]; then extra+=(-DVP_PANEL_SABOTAGE=1); output=target-panel-sabotage; fi
if [ "${VP_HEADING:-0}" = 1 ]; then extra+=(-DVP_HEADING=1); output=script-heading; fi
if [ "${VP_HEADING_SABOTAGE:-0}" = 1 ]; then extra+=(-DVP_HEADING=1 -DVP_HEADING_SABOTAGE=1); output=script-heading-sabotage; fi
"$VASM" "${extra[@]}" -DVERIFY=1 -DTIMING_RUNTIME=1 -m68000 -pic -x -devpac -Fhunkexe -nosym \
 -I"$ROOT/tmp/c" -I"$ROOT/tools" -I"$ROOT/src" -I"$AMIGA_INCLUDE" \
 -I"$WHDLOAD/Include" -I"$WHDLOAD/Src" -I"$WHDLOAD/Src/sources" -I"$AMIGA_SHARE/ndk/Include_I" \
 -L "$ROOT/tmp/c/$output.lst" -o "$ROOT/tmp/c/$output.slave" "$ROOT/tmp/c/visibility-probe.s"
