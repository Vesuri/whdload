; Optional 200 ms segment-plane coefficients, held in the public CPU owner.
; Native sine/cosine use overlapping windows of the same 1280-word Q15 table.
; Build the exact signed (Q15*1000)>>15 results once at each race activation.
; Both diagnostic arms initialize the table; control=1 keeps original work.
FF1C4BoundaryInit:
 movem.l d0-d1/a0-a1,-(sp)
 lea $2180c,a0
 lea C4BoundaryControl(pc),a1
 dc.w $d3fc
 dc.l C4BoundaryCoefficients-C4BoundaryControl
 move.w #1280-1,d1
.loop:
 move.w (a0)+,d0
 muls.w #1000,d0
 asr.l #8,d0
 asr.l #7,d0
 move.w d0,(a1)+
 dbra d1,.loop
 movem.l (sp)+,d0-d1/a0-a1
 rts
C4BoundaryControl: dc.w 1
