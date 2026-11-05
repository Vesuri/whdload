#!/usr/bin/env python3
"""Disposable pitch-only diagnostic; retain every world separation correction."""
from pathlib import Path
import argparse,shutil
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('destination',type=Path);a=p.parse_args()
assert not a.destination.exists();shutil.copytree(a.source,a.destination);s=a.destination
p=s/'4DSportsDrivingHD.s';t=p.read_text();needle='    PL_PSS $CB48,sim_a4000_wheel,142';assert needle in t;t=t.replace(needle,'    PL_PSS $D132,sim_separation_record,2\n'+needle);p.write_text(t)
p=s/'simulation_tilt.s';t=p.read_text();needle=' lea sim_tilt_wheels(pc),a3\n adda.l d0,a3';assert t.count(needle)==1;t=t.replace(needle,' lea sim_separation_vectors(pc),a3\n adda.l d0,a3\n clr.l (a3)\n clr.w 4(a3)\n'+needle)
needle=' bsr sim_tilt_pitch_vector\n move.w d0,d6\n move.w d1,d7\n';assert t.count(needle)==1;t=t.replace(needle,needle+' bsr sim_separation_pitch\n')
t+='''
; Diagnostic only: retain native world push, but remove its pitch contribution
; when BOTH response-plane endpoints are positive despite negative query.
; Per-wheel scratch is cleared during reconstruction; no replay state added.
sim_separation_record:
 move.l d0,-(sp)
 moveq #0,d0
 addx.w d0,d0
 move.w d0,-(sp)
 movem.l d0-d2/a0-a1,-(sp)
 cmp.w #50,-$15fa(a4)
 bne .done
 cmp.w #4,$96(a4)
 blt .done
 tst.b -$1ca(a5)
 bne .done
 tst.w -$5c(a5)
 ble .done
 tst.w -$62(a5)
 ble .done
 moveq #0,d0
 move.b -3(a5),d0
 mulu #6,d0
 lea sim_separation_vectors(pc),a0
 adda.l d0,a0
 move.l -$46(a5),(a0)
 move.w -$42(a5),4(a0)
.done:
 movem.l (sp)+,d0-d2/a0-a1
 move.w (sp)+,d0
 lsr.w #1,d0
 move.l (sp)+,d0
 movea.w -$46(a5),a0
 movea.l -$e6(a5),a1
 rts

sim_separation_pitch:
 movem.l d0-d7/a0-a3,-(sp)
 lea -24(sp),sp
 move.l sp,a3
 lea sim_separation_vectors(pc),a2
 moveq #3,d7
.rotate:
 move.l a3,d0
 move.l a2,a0
 lea -$28(a5),a1
 jsr -$7bd8(a4)
 addq.l #6,a2
 addq.l #6,a3
 dbra d7,.rotate
 move.l sp,a0
 bsr sim_tilt_pitch_vector
 sub.w d0,50(sp) ; saved final D6 low word, after24 bytes of temporary vectors
 sub.w d1,54(sp) ; saved final D7 low word
 lea 24(sp),sp
 movem.l (sp)+,d0-d7/a0-a3
 rts
 even
sim_separation_vectors: dcb.w 12,0
''';p.write_text(t)
print(a.destination)
