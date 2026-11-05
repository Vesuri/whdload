        IFD VERIFY
        IFD SCAN_TEST
        IFND SCAN_TWIN
        FAIL "SCAN_TEST requires SCAN_TWIN and SCAN_FAST"
        ENDC
s60_scan_actors: ds.b 6*$6e
; Query radius, candidate radius, and candidate X/Z/Y. Include native signed
; overflow behavior, not an idealized unsigned/geometric reinterpretation.
s60_scan_cases:
        dc.l 100,100,0,0,0
        dc.l 100,100,100,0,0
        dc.l 100,100,101,0,0
        dc.l 100,100,-100,0,0
        dc.l 100,100,-101,0,0
        dc.l 100,100,0,100,0
        dc.l 100,100,0,101,0
        dc.l 100,100,0,0,-100
        dc.l 100,100,0,0,-101
        dc.l 0,0,0,0,0
        dc.l 0,0,1,0,0
        dc.l $7fffffff,1,$80000000,$80000000,$80000000
        dc.l -1,1,0,0,0
        dc.l $80000000,$80000000,$80000000,0,0
        dc.l $7fffffff,$7fffffff,$80000000,$80000000,$80000000
        dc.l 100,100,$7fffffff,0,0
s60_test_scan:
        move.l (s60_ticks,pc),d0
        cmp.l #SCAN_TEST,d0
        bne .done
        move.w (s60_scan_results+12,pc),d0
        bne .done
        movem.l d2-d7/a2-a6,-(sp)
        move.w ($43b2-S60_DATA,a4),-(sp)
        suba.w #1024,sp
        move.l sp,a6
        move.l a6,a1
        lea ($3fb2-S60_DATA,a4),a0
        move.w #255,d0
.save:  move.l (a0)+,(a1)+
        dbf d0,.save
        moveq #0,d5
.case:  lea (s60_scan_actors,pc),a0
        move.w #6*$6e/2-1,d0
.clear: clr.w (a0)+
        dbf d0,.clear
        lea (s60_scan_actors,pc),a2
        move.l a2,a0
        lea ($3fb2-S60_DATA,a4),a1
        moveq #5,d0
.actors:
        move.w #1,(2,a0)
        move.l #100,(4,a0)
        move.l #$12345678,($66,a0)
        move.l a0,(a1)+
        adda.w #$6e,a0
        dbf d0,.actors
        move.b #$fd,(2*$6e+$54,a2)
        move.b #$fc,(3*$6e+$54,a2)
        move.w #7,(4*$6e+2,a2)
        move.l #10000,(5*$6e+8,a2)
        move.w #6,($43b2-S60_DATA,a4)
        move.w d5,d0
        and.w #15,d0
        mulu #20,d0
        lea (s60_scan_cases,pc),a0
        adda.w d0,a0
        move.l (a0)+,(4,a2)
        move.l (a0)+,($6e+4,a2)
        move.l (a0)+,($6e+8,a2)
        move.l (a0)+,($6e+12,a2)
        move.l (a0)+,($6e+16,a2)
        IFD SCAN_FLAG_TEST
        cmp.w #68,d5
        bcs .original_case
        move.w d5,d0
        sub.w #68,d0
        move.b d0,($6e+$54,a2)
        clr.l ($6e+8,a2)
        clr.l ($6e+12,a2)
        clr.l ($6e+16,a2)
        move.l #100,(4,a2)
        move.l #100,($6e+4,a2)
        bra .call
.original_case:
        ENDC
        cmp.w #16,d5
        bcs .call
        cmp.w #32,d5
        bcc .query7
        clr.l (5*$6e+8,a2) ; multiple overlaps: keep all links, return last
        bra .call
.query7:
        cmp.w #48,d5
        bcc .reverse
        move.w #7,(2,a2)
        bra .call
.reverse:
        cmp.w #64,d5
        bcc .edge_count
        lea (5*$6e,a2),a0
        lea ($3fb2-S60_DATA,a4),a1
        moveq #5,d0
.rev:   move.l a0,(a1)+
        suba.w #$6e,a0
        dbf d0,.rev
        clr.l (5*$6e+8,a2)
        bra .call
.edge_count:
        cmp.w #64,d5
        bne .negative
        clr.w ($43b2-S60_DATA,a4)
        bra .call
.negative:
        cmp.w #65,d5
        bne .full
        move.w #-1,($43b2-S60_DATA,a4)
        bra .call
.full:  cmp.w #66,d5
        bne .self
        move.w #256,($43b2-S60_DATA,a4)
        lea ($3fb2-S60_DATA,a4),a1
        lea ($6e,a2),a0
        move.w #255,d0
.dups:  move.l a0,(a1)+ ; duplicate pointers must not invalidate the oracle
        dbf d0,.dups
        bra .call
.self:  move.w #1,($43b2-S60_DATA,a4)
.call:
        move.l (s60_scan_results+8,pc),d6
        move.l a2,-(sp)
        bsr s60_scan_twin
        addq.l #4,sp
        lea (s60_scan_results,pc),a0
        addq.w #1,(12,a0)
        cmp.l (8,a0),d6
        beq .next
        addq.w #1,(14,a0)
.next:  addq.w #1,d5
        IFD SCAN_FLAG_TEST
        cmp.w #324,d5
        ELSE
        cmp.w #68,d5
        ENDC
        bne .case
        move.l a6,a0
        lea ($3fb2-S60_DATA,a4),a1
        move.w #255,d0
.restore:
        move.l (a0)+,(a1)+
        dbf d0,.restore
        adda.w #1024,sp
        move.w (sp)+,($43b2-S60_DATA,a4)
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
