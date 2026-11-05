#!/usr/bin/env python3
"""Isolated consistent contact-plane experiment; not an accepted runtime."""
from pathlib import Path
import shutil
source=Path('src');dst=Path('tmp/fixtures/response-plane-d9/source');assert not dst.exists();shutil.copytree(source,dst)
p=dst/'4DSportsDrivingHD.s';s=p.read_text();needle='    PL_PSS $CB06,sim_a4000_wheel_pass,2';assert s.count(needle)==1;s=s.replace(needle,'''    PL_PS $C722,sim_response_wheel_plane
    PL_PS $CC0E,sim_response_wheel_plane
    PL_PS $CE34,sim_response_wheel_plane
    PL_PSS $D0DE,sim_response_wheel_plane,4
'''+needle);p.write_text(s)
p=dst/'simulation_a4000.s';s=p.read_text();s+='''
; ISOLATED: use the response matrix's normal for inclined wheel queries.
; The native response inverse transform Y is dot(local, matrix row1)/16384,
; arithmetic floor, with the same signed-word coarse coordinates and origin.
; Native modes and flat-plane results remain on the original query.
sim_response_wheel_plane:
 cmp.w #50,-$15fa(a4)
 bne .store
 cmp.w #4,$96(a4)
 blt .store
 movem.l d1-d7/a0-a3,-(sp)
 moveq #0,d7
 addx.w d7,d7
 move.w d7,-(sp)
 lea -6(sp),sp
 move.l $1ee(a4),a1
 move.w $94(a4),d1
 add.w 4(a1),d1
 move.w d1,(sp)
 move.w $92(a4),d1
 add.w 6(a1),d1
 move.w d1,2(sp)
 move.w $90(a4),d1
 add.w 8(a1),d1
 move.w d1,4(sp)
 ; Matrix starts at plane+16; its second row at+22.
 lea 22(a1),a1
 move.l sp,a2
 move.l -$e6(a5),a0
 moveq #0,d4
 moveq #2,d6
.axis:
 move.l (a0)+,d0
 asr.l #6,d0
 sub.w (a2)+,d0
 move.w (a1)+,d2
 muls d2,d0
 add.l d0,d4
 dbra d6,.axis
 move.l d4,d0
 asr.l #8,d0
 asr.l #6,d0
 lea 6(sp),sp
 move.w (sp)+,d7
 lsr.b #1,d7
 movem.l (sp)+,d1-d7/a0-a3
.store:
 move.w d0,$bc0(a4)
 move.l (sp),8(sp)
 lea 8(sp),sp
 tst.w $bc0(a4)
 rts
''';p.write_text(s)
# Instrumentation validates against the matrix in the captured static plane table.
s=Path('tools/release_step_probe.py').read_text();s=s.replace('import json,re,sys','import json,re,sys,struct');s=s.replace("# Reconstruct the native signed-word inputs and truncating signed quotient.","# Reconstruct the experimental response-matrix query, preserving flat planes.")
s=s.replace("normal=[r['normal_'+a] for a in 'xyz']\n  dot=sum(v*n for v,n in zip(delta,normal));predicted=w(trunc(dot,8192))", "table=struct.unpack_from('>I',mem,m['data_base']+0x7ffe-m['memory_base']+0x224)[0]-m['memory_base']\n  normal=struct.unpack_from('>3h',mem,table+34*r['plane']+22)\n  dot=sum(v*n for v,n in zip(delta,normal));predicted=w(dot//16384)")
s=s.replace("/8192\n native_prediction", "/16384\n native_prediction").replace("else 'native-coordinate-floors'", "else 'response-matrix-coordinate-floors'")
Path('tools/response_plane_probe.py').write_text(s)
