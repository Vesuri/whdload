from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1];src=root/'src';out=root/'tmp/p2-rect-twin-source'
assert not out.exists();shutil.copytree(src,out)
p=out/'performance.s';s=p.read_text();s=s.replace('perf_cpu_rect:\n adda.w d1,a0','perf_cpu_rect:\n bsr rect_twin_before\n adda.w d1,a0').replace(' movem.l (sp)+,d0-d4/a0\n tst.w d3\n rts',' movem.l (sp)+,d0-d4/a0\n bsr rect_twin_after\n tst.w d3\n rts')
s+='''
; Diagnostic source copy only: the production source has no twin buffers.
rect_twin_before:
 movem.l d0-d7/a0-a6,-(sp)
 moveq #0,d7
 addx.b d7,d7
 move.w d7,-(sp)
 lea rect_twin_active(pc),a1
 clr.w (a1)
 cmp.w #40,$bf6(a4)
 bne .done
 cmp.w #200,$bf8(a4)
 bne .done
 lea $bfe(a4),a1
 moveq #3,d0
.match:
 cmpa.l (a1)+,a0
 beq .matched
 dbra d0,.match
 bra .done
.matched:
 lea rect_twin_active(pc),a1
 move.w #1,(a1)
 lea rect_twin_plane(pc),a1
 move.l a0,(a1)
 tst.b $dff002
.wait:
 btst #6,$dff002
 bne.s .wait
 lea rect_twin_initial(pc),a1
 move.w #1999,d0
.copy:
 move.l (a0)+,(a1)+
 dbra d0,.copy
.done:
 move.w (sp)+,d7
 lsr.w #1,d7
 movem.l (sp)+,d0-d7/a0-a6
 rts

rect_twin_after:
 movem.l d0-d7/a0-a6,-(sp)
 moveq #0,d7
 addx.b d7,d7
 move.w d7,-(sp)
 lea rect_twin_active(pc),a1
 tst.w (a1)
 beq .done
 clr.w (a1)
 ; Capture the complete CPU result, then restore the exact initial plane.
 move.l a0,a3
 move.l rect_twin_plane(pc),a0
 lea rect_twin_cpu(pc),a1
 lea rect_twin_initial(pc),a2
 move.w #1999,d0
.copy:
 move.l (a0),(a1)+
 move.l (a2)+,(a0)+
 dbra d0,.copy
 ; These are precisely the native writes at $347CC/$347D0/$347D4.
 ; The original prefix already set BLTCON1 and BLTDMOD for this D-only fill.
 move.l a3,$dff054
 move.w d2,$dff040
 move.w d3,$dff058
 tst.b $dff002
.wait:
 btst #6,$dff002
 bne.s .wait
 move.l rect_twin_plane(pc),a0
 lea rect_twin_cpu(pc),a1
 move.w #1999,d0
.compare:
 cmpm.l (a0)+,(a1)+
 bne .failed
 dbra d0,.compare
 lea rect_twin_passed(pc),a0
 addq.l #1,(a0)
.done:
 move.w (sp)+,d7
 lsr.w #1,d7
 movem.l (sp)+,d0-d7/a0-a6
 rts
.failed:
 lea rect_twin_failed(pc),a0
 addq.l #1,(a0)
 lea perf_failure(pc),a0
 move.l #201,(a0)
 illegal
 bra .failed
 even
 dc.b "4DRECTWN"
rect_twin_passed: dc.l 0
rect_twin_failed: dc.l 0
rect_twin_active: dc.w 0
rect_twin_plane: dc.l 0
rect_twin_initial: dcb.b 8000,0
rect_twin_cpu: dcb.b 8000,0
'''
p.write_text(s)
print(out)
