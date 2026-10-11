; Full movement-wrapper A/B fixtures, including private rollback state and CCR.
; Compare the complete ordinary wrapper with two identical-seed fast calls.
        IFD VERIFY
        IFD LINEAR_TEST
        IFEQ MOVE_LINEAR
        FAIL "LINEAR_TEST requires MOVE_LINEAR=1"
        ENDC
s60_linear_enable: dc.w 1
s60_linear_results:
        dc.b 'L861'
        dc.w 0,0,0,0,0 ; cases, actor/record/CCR errors, preserved-register errors
s60_linear_actor: ds.b $6e
s60_linear_seed: ds.b $6e+S60_REC
s60_linear_expected: ds.b $6e+S60_REC
s60_linear_ccr: dc.w 0
s60_linear_yaws:
        dc.w $8000,$8001,$bfff,$c000,$c001,-17,-16,-1
        dc.w 0,1,15,16,$3fff,$4000,$4001,$7fff
s60_linear_speeds: dc.w $8000,-1,0,1,500,$7fff
s60_linear_fractions:
        dc.w 0,0,1,-1,-1,1,11,-11,-11,11,11,11,-11,-11,5,-5
        dc.w -5,5,0,11,0,-11,11,0,-11,0,7,3,-7,-3,3,-7
; Positive offsets are actor fields; negative offsets are private record words.
s60_linear_offsets: dc.w -8,-12,-18,-14,-16,20,20,58,60,62,56,52,54,2,-8,-18
s60_linear_values: dc.w 1,1,1,12,-12,1,-1,1,-1,$7fff,1,-1,1,7,$8000,$8000
s60_linear_invoke:
        move.l a0,-(sp)
        movem.l d5-d7/a4,-(sp)
        move.l a3,-(sp)
        move.w d6,ccr
        bsr s60_move
s60_linear_return:
        move.w sr,d1 ; capture before any flag-changing instruction
        IFD LINEAR_BAD_REGISTER
        addq.l #1,d5 ; negative control: must fail the preserved-register check
        ENDC
        addq.l #4,sp
        cmp.l (sp),d5
        bne .register_error
        cmp.l (4,sp),d6
        bne .register_error
        cmp.l (8,sp),d7
        bne .register_error
        cmpa.l (12,sp),a4
        beq .register_ok
.register_error:
        lea (s60_linear_results,pc),a0
        addq.w #1,(12,a0)
.register_ok:
        movem.l (sp)+,d5-d7/a4
        move.l (sp)+,a0
        rts
s60_linear_copy_out:
        move.l a3,a0
        moveq #$6e/2-1,d0
.actor: move.w (a0)+,(a1)+
        dbf d0,.actor
        move.l a6,a0
        moveq #S60_REC/2-1,d0
.record: move.w (a0)+,(a1)+
        dbf d0,.record
        rts
s60_linear_restore:
        lea (s60_linear_seed,pc),a0
        move.l a3,a1
        moveq #$6e/2-1,d0
.actor: move.w (a0)+,(a1)+
        dbf d0,.actor
        move.l a6,a1
        moveq #S60_REC/2-1,d0
.record: move.w (a0)+,(a1)+
        dbf d0,.record
        rts
s60_test_linear:
        move.l (s60_ticks,pc),d0
        cmp.l #LINEAR_TEST,d0
        bne .done
        move.w (s60_linear_results+4,pc),d0
        bne .done
        movem.l d0-d7/a0-a6,-(sp)
        lea (s60_linear_actor,pc),a3
        bsr s60_motion_record
        moveq #0,d5
.case:
        move.l a3,a0
        moveq #$6e/2-1,d0
.clear_actor: clr.w (a0)+
        dbf d0,.clear_actor
        move.l a6,a0
        moveq #S60_REC/2-1,d0
.clear_record: clr.w (a0)+
        dbf d0,.clear_record
        move.l a3,(a6)
        move.w #1,(2,a3)
        move.l #$7ffffff0,(8,a3)
        move.l #$80000010,(12,a3)
        move.l #$ffffffff,(16,a3)
        ; Stale displacement/backups must be replaced exactly by both paths.
        lea (20,a6),a0
        moveq #20,d0
.stale: move.w #$a55a,(a0)+
        dbf d0,.stale
        move.w d5,d0
        and.w #15,d0
        add.w d0,d0
        lea (s60_linear_yaws,pc),a0
        move.w (a0,d0.w),(24,a3)
        moveq #0,d0
        move.w d5,d0
        lsr.w #4,d0
        divu #6,d0
        move.w d0,d4 ; 32 remainder/guard scenarios
        swap d0
        add.w d0,d0
        lea (s60_linear_speeds,pc),a0
        move.w (a0,d0.w),(64,a3)
        moveq #0,d6
        btst #0,d4
        beq .ccr_ready
        moveq #$1f,d6
.ccr_ready:
        btst #3,d4
        beq .bank_ready
        move.w #$8000,(22,a3)
.bank_ready:
        cmp.w #16,d4
        bcc .fallback_case
        move.w d4,d0
        lsl.w #2,d0
        lea (s60_linear_fractions,pc),a0
        move.l (a0,d0.w),(14,a6)
        bra .ready
.fallback_case:
        sub.w #16,d4
        add.w d4,d4
        lea (s60_linear_offsets,pc),a0
        move.w (a0,d4.w),d0
        lea (s60_linear_values,pc),a0
        move.w (a0,d4.w),d1
        tst.w d0
        bmi .record_case
        move.w d1,(a3,d0.w)
        cmp.w #2,d0
        bne .ready
        move.w #1,(4,a6) ; type-7 phase is already initialized
        bra .ready
.record_case:
        neg.w d0
        move.w d1,(a6,d0.w)
.ready:
        lea (s60_linear_seed,pc),a1
        bsr s60_linear_copy_out
        lea (s60_linear_enable,pc),a0
        clr.w (a0)
        bsr s60_linear_invoke
        and.w #$1f,d1
        lea (s60_linear_ccr,pc),a0
        move.w d1,(a0)
        lea (s60_linear_expected,pc),a1
        bsr s60_linear_copy_out
        moveq #1,d7
.repeat:
        bsr s60_linear_restore
        lea (s60_linear_enable,pc),a0
        move.w #1,(a0)
        bsr s60_linear_invoke
        and.w #$1f,d1
        cmp.w (s60_linear_ccr,pc),d1
        beq .actor_compare
        lea (s60_linear_results,pc),a0
        addq.w #1,(10,a0)
.actor_compare:
        lea (s60_linear_expected,pc),a0
        move.l a3,a1
        moveq #$6e/2-1,d0
.actor_word:
        cmpm.w (a0)+,(a1)+
        beq .actor_next
        lea (s60_linear_results,pc),a2
        addq.w #1,(6,a2)
        bra .record_begin
.actor_next: dbf d0,.actor_word
.record_begin:
        lea (s60_linear_expected+$6e,pc),a0
        move.l a6,a1
        moveq #S60_REC/2-1,d0
.record_word:
        cmpm.w (a0)+,(a1)+
        beq .record_next
        lea (s60_linear_results,pc),a2
        addq.w #1,(8,a2)
        bra .compared
.record_next: dbf d0,.record_word
.compared:
        lea (s60_linear_results,pc),a0
        addq.w #1,(4,a0)
        dbf d7,.repeat
        addq.w #1,d5
        cmp.w #3072,d5
        bcs .case
        move.l a6,a0
        moveq #S60_REC/2-1,d0
.clear_final: clr.w (a0)+
        dbf d0,.clear_final
        movem.l (sp)+,d0-d7/a0-a6
.done:  rts
        ENDC
        ENDC
