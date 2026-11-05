        IFD VERIFY
        IFD RECENTER_TEST
; Full actor bytes plus native D1/CCR and preserved working-register checks.
; 128 combinations: list counts, wrapping, secondary aliases and incoming X.
s60_recenter_results: dc.b 'RC60'
        dc.w 0,0
        ds.w 128
s60_recenter_error: dc.w 0
s60_recenter_expected_d1: dc.l 0
s60_recenter_expected_ccr: dc.w 0
s60_recenter_actors: ds.b 18*112
s60_recenter_before: ds.b 18*112
s60_recenter_expected: ds.b 18*112
s60_recenter_counts: dc.w 0,1,16,256
s60_recenter_values:
        dc.l -32769,-32768,-32767,0,32767,32768,32769,$80000000
s60_recenter_probe:
        movem.l d2-d3/a1-a2,-(sp)
        move.l d5,d1
        eor.l #$98765432,d1
        moveq #0,d0
        btst #6,d5
        beq .seed
        moveq #16,d0
.seed:  move.w d0,ccr
        jsr (a0)
        move.w sr,-(sp)
        cmpa.l ($43c0-S60_DATA,a4),a0
        bne .bad
        cmp.l (2,sp),d2
        bne .bad
        cmp.l (6,sp),d3
        bne .bad
        cmpa.l (10,sp),a1
        bne .bad
        cmpa.l (14,sp),a2
        beq .done
.bad:   lea (s60_recenter_error,pc),a0
        or.w #4,(a0)
.done:  move.w (sp)+,d0
        and.w #31,d0
        movem.l (sp)+,d2-d3/a1-a2
        rts
s60_test_recenter:
        move.l (s60_ticks,pc),d0
        cmp.l #RECENTER_TEST,d0
        bne .done
        move.w (s60_recenter_results+4,pc),d0
        bne .done
        movem.l d2-d7/a2-a6,-(sp)
        move.w ($43b2-S60_DATA,a4),-(sp)
        move.w ($1e96-S60_DATA,a4),-(sp)
        move.w ($1e9c-S60_DATA,a4),-(sp)
        move.l ($43c0-S60_DATA,a4),-(sp)
        move.l ($43c4-S60_DATA,a4),-(sp)
        lea (-1024,sp),sp
        move.l sp,a1
        lea ($3fb2-S60_DATA,a4),a0
        move.w #255,d0
.save_list:
        move.l (a0)+,(a1)+
        dbf d0,.save_list
        moveq #0,d5
.case:
        lea (s60_recenter_error,pc),a0
        clr.w (a0)
        lea (s60_recenter_actors,pc),a0
        move.w #18*112/4-1,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        lea (s60_recenter_actors,pc),a3
        moveq #0,d6
.actor:
        move.w #1,(2,a3)
        move.w d6,d0
        and.w #3,d0
        bne .position
        move.w #7,(2,a3)
.position:
        move.w d5,d0
        lsr.w #2,d0
        add.w d6,d0
        and.w #7,d0
        lsl.w #2,d0
        lea (s60_recenter_values,pc),a0
        move.l (a0,d0.w),(8,a3)
        addq.w #4,d0
        and.w #31,d0
        move.l (a0,d0.w),(12,a3)
        adda.w #112,a3
        addq.w #1,d6
        cmp.w #18,d6
        bne .actor
        lea (s60_recenter_actors+16*112,pc),a2
        move.l a2,($43c0-S60_DATA,a4)
        lea (s60_recenter_actors+17*112,pc),a0
        btst #2,d5
        beq .secondary
        lea (s60_recenter_actors,pc),a0
        btst #3,d5
        beq .secondary
        move.l a2,a0
.secondary:
        move.l a0,($43c4-S60_DATA,a4)
        clr.w ($1e9c-S60_DATA,a4)
        btst #5,d5
        beq .phase
        move.w #1,($1e9c-S60_DATA,a4)
.phase: clr.w ($1e96-S60_DATA,a4)
        btst #4,d5
        beq .list
        move.w #1,($1e96-S60_DATA,a4)
.list:  move.w d5,d0
        and.w #3,d0
        add.w d0,d0
        lea (s60_recenter_counts,pc),a0
        move.w (a0,d0.w),($43b2-S60_DATA,a4)
        lea ($3fb2-S60_DATA,a4),a1
        moveq #0,d6
.list_item:
        move.w d6,d0
        and.w #15,d0
        cmp.w #15,d0
        bne .ordinary
        move.l a2,(a1)+
        bra .listed
.ordinary:
        mulu #112,d0
        lea (s60_recenter_actors,pc),a0
        adda.w d0,a0
        move.l a0,(a1)+
.listed:
        addq.w #1,d6
        cmp.w #256,d6
        bne .list_item
        lea (s60_recenter_actors,pc),a0
        lea (s60_recenter_before,pc),a1
        move.w #18*112/4-1,d0
.save_before:
        move.l (a0)+,(a1)+
        dbf d0,.save_before
        move.l (s60_code,pc),a0
        adda.l #$3ab8,a0
        bsr s60_recenter_probe
        lea (s60_recenter_expected_ccr,pc),a0
        move.w d0,(a0)
        lea (s60_recenter_expected_d1,pc),a0
        move.l d1,(a0)
        lea (s60_recenter_actors,pc),a0
        lea (s60_recenter_expected,pc),a1
        lea (s60_recenter_before,pc),a2
        move.w #18*112/4-1,d0
.save_expected:
        move.l (a0),(a1)+
        move.l (a2)+,(a0)+
        dbf d0,.save_expected
        lea (s60_recenter,pc),a0
        bsr s60_recenter_probe
        cmp.w (s60_recenter_expected_ccr,pc),d0
        bne .return_error
        cmp.l (s60_recenter_expected_d1,pc),d1
        beq .compare
.return_error:
        lea (s60_recenter_error,pc),a0
        or.w #2,(a0)
.compare:
        lea (s60_recenter_actors,pc),a0
        IFD RECENTER_BAD
        addq.l #1,(8,a0)
        ENDC
        lea (s60_recenter_expected,pc),a1
        move.w #18*112/4-1,d0
.check: cmpm.l (a0)+,(a1)+
        bne .actor_error
        dbf d0,.check
        bra .count
.actor_error:
        lea (s60_recenter_error,pc),a0
        or.w #1,(a0)
.count: lea (s60_recenter_results,pc),a0
        move.w d5,d0
        add.w d0,d0
        move.w (s60_recenter_error,pc),d1
        move.w d1,(8,a0,d0.w)
        beq .pass
        addq.w #1,(6,a0)
.pass:  addq.w #1,(4,a0)
        addq.w #1,d5
        cmp.w #128,d5
        bne .case
        move.l sp,a0
        lea ($3fb2-S60_DATA,a4),a1
        move.w #255,d0
.restore_list:
        move.l (a0)+,(a1)+
        dbf d0,.restore_list
        lea (1024,sp),sp
        move.l (sp)+,($43c4-S60_DATA,a4)
        move.l (sp)+,($43c0-S60_DATA,a4)
        move.w (sp)+,($1e9c-S60_DATA,a4)
        move.w (sp)+,($1e96-S60_DATA,a4)
        move.w (sp)+,($43b2-S60_DATA,a4)
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
