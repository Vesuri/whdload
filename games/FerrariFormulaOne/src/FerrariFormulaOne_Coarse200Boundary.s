; Optional 200 ms segment-plane coefficients, held in the public CPU owner.
; Native sine/cosine use overlapping windows of the same 1280-word Q15 table.
; Build the exact signed (Q15*1000)>>15 results once at each race activation.
; Both diagnostic arms initialize the table; control=1 keeps original work.
FF1C4BoundaryInit:
 movem.l d0-d1/a0-a1,-(sp)
 lea C4BoundaryControl(pc),a1
 tst.l 2(a1)
 bne.b .owned
 ; The table is allocated once, on the first race, and kept. Without it the
 ; native coefficients stay selected.
 lea 2(a1),a0
 move.l #1280*2,d0
 bsr.w FF1PublicAcquire
 tst.l d0
 bne.b .owned
 lea C4BoundaryControl(pc),a1
 move.w #1,(a1)
 bra.b .done
.owned:
 lea $2180c,a0
 lea C4BoundaryControl(pc),a1
 move.l 2(a1),a1
 move.w #1280-1,d1
.loop:
 move.w (a0)+,d0
 muls.w #1000,d0
 asr.l #8,d0
 asr.l #7,d0
 move.w d0,(a1)+
 dbra d1,.loop
.done:
 movem.l (sp)+,d0-d1/a0-a1
 rts
C4BoundaryControl: dc.w 1
; Allocation owner (FF1PublicAcquire): the 1280-word table and its size.
C4BoundaryCoefficients: dc.l 0,0
