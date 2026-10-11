        IFD VERIFY
        IFD PICKUP_TEST
; Native position/state oracle. Removal, inventory presentation and audio
; entry points are stubbed only for the isolated fake actor, then restored.
s60_pickup_results:
        dc.b 'P761'
        dc.w 0,0 ; completed cases, mismatches
        dc.w 0,0 ; checked substeps and full-state boundaries
s60_pickup_actor: ds.b 112
s60_pickup_saved: ds.b 16
s60_pickup_expected: ds.b 30*128
s60_pickup_actual: ds.b 128
s60_pickup_start: ds.b 8
; initial counter, yaw increment, Y increment, yaw, height
s60_pickup_cases:
        dc.w 0,20,10,-6
        dc.l 100
        dc.w 26,6676,140,32760
        dc.l 100
        dc.w 0,-100,-7,20
        dc.l -100
        dc.w 0,-32768,32767,0
        dc.l 0
s60_pickup_gate:
        movem.l d1/a0/a2,-(sp)
        move.l (s60_code,pc),a0
        tst.w d0
        beq .restore
        cmp.w #$4ef9,($4238,a0)
        bne s60_bad
        move.w #$4e75,($4238,a0)
        adda.l #$8000,a0
        cmp.w #$4ef9,($03c6,a0)
        bne s60_bad
        cmp.w #$4ef9,($1492,a0)
        bne s60_bad
        move.w #$4e75,($03c6,a0)
        move.w #$4e75,($1492,a0)
        bra .flush
.restore:
        move.w #$4ef9,($4238,a0)
        adda.l #$8000,a0
        move.w #$4ef9,($03c6,a0)
        move.w #$4ef9,($1492,a0)
.flush:
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d1/a0/a2
        rts
s60_pickup_setup:
        bsr s60_pickup_reset
        lea (s60_pickup_actor,pc),a3
        move.l a3,a0
        moveq #27,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        move.w #31,(2,a3)
        move.b #100,($55,a3)
        lea (s60_pickup_cases,pc),a0
        move.w d5,d0
        mulu #12,d0
        adda.w d0,a0
        move.l (a0)+,($0346-S60_DATA,a4)
        move.w (a0)+,($034a-S60_DATA,a4)
        move.w (a0)+,($18,a3)
        move.l (a0),($10,a3)
        move.l a3,($46c0-S60_DATA,a4)
        move.w #300,($46c4-S60_DATA,a4)
        move.b #1,($1e56-S60_DATA,a4)
        move.w #1,($0268-S60_DATA,a4)
        rts
; a1 = destination; snapshot 112 actor bytes and sixteen global-state bytes.
s60_pickup_snapshot:
        move.l a3,a0
        moveq #27,d0
.copy:  move.l (a0)+,(a1)+
        dbf d0,.copy
        move.l ($0346-S60_DATA,a4),(a1)+
        move.w ($034a-S60_DATA,a4),(a1)+
        move.w ($46c4-S60_DATA,a4),(a1)+
        move.w ($1e56-S60_DATA,a4),(a1)+
        move.w ($0268-S60_DATA,a4),(a1)+
        move.l ($46c0-S60_DATA,a4),(a1)+
        rts
s60_pickup_error:
        lea (s60_pickup_results,pc),a0
        addq.w #1,(6,a0)
        rts
s60_test_pickup:
        move.l (s60_ticks,pc),d0
        cmp.l #PICKUP_TEST,d0
        bne .done
        move.w (s60_pickup_results+4,pc),d0
        bne .done ; one fixture pass per boot, including after death/retry
        movem.l d2-d7/a2-a6,-(sp)
        move.l ($46c0-S60_DATA,a4),-(sp)
        move.l ($0346-S60_DATA,a4),-(sp)
        move.w ($034a-S60_DATA,a4),-(sp)
        move.w ($46c4-S60_DATA,a4),-(sp)
        move.w ($1e56-S60_DATA,a4),-(sp)
        move.w ($0268-S60_DATA,a4),-(sp)
        lea (s60_pickup_state,pc),a0
        lea (s60_pickup_saved,pc),a1
        moveq #3,d0
.save:  move.l (a0)+,(a1)+
        dbf d0,.save
        moveq #1,d0
        bsr s60_pickup_gate
        moveq #0,d5
.case:
        moveq #4,d4
        tst.w d5
        bne .periods_ready
        moveq #30,d4 ; complete the normal six-second pickup sequence
.periods_ready:
        bsr s60_pickup_setup
        lea (s60_pickup_expected,pc),a2
        move.w d4,d6
        subq.w #1,d6
.reference:
        S60_CALL $3d2a
        move.l a2,a1
        bsr s60_pickup_snapshot
        adda.w #128,a2
        dbf d6,.reference
        bsr s60_pickup_setup
        lea (s60_pickup_expected,pc),a2
        moveq #0,d6
.period:
        lea (s60_pickup_start,pc),a0
        move.l ($10,a3),(a0)
        move.w ($18,a3),(4,a0)
        moveq #1,d7
.tick:
        bsr s60_pickup_update
        move.l ($10,a2),d0
        sub.l (s60_pickup_start,pc),d0
        muls d7,d0
        divs #S60_SUBSTEPS,d0
        ext.l d0
        add.l (s60_pickup_start,pc),d0
        cmp.l ($10,a3),d0
        beq .yaw
        bsr s60_pickup_error
.yaw:
        move.w ($18,a2),d0
        sub.w (s60_pickup_start+4,pc),d0
        muls d7,d0
        divs #S60_SUBSTEPS,d0
        add.w (s60_pickup_start+4,pc),d0
        cmp.w ($18,a3),d0
        beq .deadline
        bsr s60_pickup_error
.deadline:
        cmp.w #S60_SUBSTEPS,d7
        beq .next_tick
        ; Native counter/deletion/first healing must wait for the boundary.
        lea (s60_pickup_cases,pc),a0
        move.w d5,d0
        mulu #12,d0
        adda.w d0,a0
        move.w (a0),d0
        add.w d6,d0
        cmp.w ($0346-S60_DATA,a4),d0
        bne .deadline_error
        cmp.l ($46c0-S60_DATA,a4),a3
        bne .deadline_error
        tst.w d6
        bne .next_tick
        cmp.w #300,($46c4-S60_DATA,a4)
        beq .next_tick
.deadline_error:
        bsr s60_pickup_error
.next_tick:
        lea (s60_pickup_results,pc),a0
        addq.w #1,(8,a0)
        addq.w #1,d7
        cmp.w #S60_SUBSTEPS+1,d7
        bne .tick
        lea (s60_pickup_actual,pc),a1
        bsr s60_pickup_snapshot
        lea (s60_pickup_actual,pc),a0
        move.l a2,a1
        moveq #31,d2
.compare:
        move.l (a0)+,d0
        cmp.l (a1)+,d0
        beq .equal
        move.l a0,a6
        bsr s60_pickup_error
        move.l a6,a0
.equal: dbf d2,.compare
        adda.w #128,a2
        addq.w #1,d6
        lea (s60_pickup_results,pc),a0
        addq.w #1,(10,a0)
        cmp.w d4,d6
        bne .period
        lea (s60_pickup_results,pc),a0
        addq.w #1,(4,a0)
        addq.w #1,d5
        cmp.w #4,d5
        bne .case
        moveq #0,d0
        bsr s60_pickup_gate
        move.w (sp)+,($0268-S60_DATA,a4)
        move.w (sp)+,($1e56-S60_DATA,a4)
        move.w (sp)+,($46c4-S60_DATA,a4)
        move.w (sp)+,($034a-S60_DATA,a4)
        move.l (sp)+,($0346-S60_DATA,a4)
        move.l (sp)+,($46c0-S60_DATA,a4)
        lea (s60_pickup_saved,pc),a0
        lea (s60_pickup_state,pc),a1
        moveq #3,d0
.restore:
        move.l (a0)+,(a1)+
        dbf d0,.restore
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
