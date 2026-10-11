; Full movement-wrapper A/B fixtures, including private rollback state and CCR.
; The baseline skips only MOVE_IDLE's guard; all other movement code is shared.
        IFD VERIFY
        IFD IDLE_TEST
        IFEQ MOVE_IDLE
        FAIL "IDLE_TEST requires MOVE_IDLE=1"
        ENDC
s60_idle_enable: dc.w 1
s60_idle_results:
        dc.b 'I760'
        dc.w 0,0,0,0 ; cases, actor errors, record errors, CCR errors
s60_idle_actor: ds.b $6e
s60_idle_seed: ds.b $6e+S60_REC
s60_idle_expected: ds.b $6e+S60_REC
s60_idle_ccr: dc.w 0
s60_idle_invoke:
        move.l a3,-(sp)
        move.w d6,ccr
        bsr s60_move
s60_idle_return:
        move.w sr,d1 ; capture before any flag-changing instruction
        addq.l #4,sp
        rts
s60_idle_copy_out:
        move.l a3,a0
        moveq #$6e/2-1,d0
.actor: move.w (a0)+,(a1)+
        dbf d0,.actor
        move.l a6,a0
        moveq #S60_REC/2-1,d0
.record: move.w (a0)+,(a1)+
        dbf d0,.record
        rts
s60_idle_restore:
        lea (s60_idle_seed,pc),a0
        move.l a3,a1
        moveq #$6e/2-1,d0
.actor: move.w (a0)+,(a1)+
        dbf d0,.actor
        move.l a6,a1
        moveq #S60_REC/2-1,d0
.record: move.w (a0)+,(a1)+
        dbf d0,.record
        rts
s60_test_idle:
        move.l (s60_ticks,pc),d0
        cmp.l #IDLE_TEST,d0
        bne .done
        move.w (s60_idle_results+4,pc),d0
        bne .done
        movem.l d0-d7/a0-a6,-(sp)
        lea (s60_idle_actor,pc),a3
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
        move.w #$8000,(20,a3)
        move.w #$7fff,(22,a3)
        move.w #$1234,(24,a3)
        ; Stale displacement, snapshots and backups must be replaced correctly.
        lea (20,a6),a0
        moveq #20,d0
.stale: move.w #$a55a,(a0)+
        dbf d0,.stale
        move.w d5,d4
        and.w #31,d4
        moveq #1,d7
        moveq #0,d6
        cmp.w #32,d5
        bcs .select
        moveq #-1,d7
        moveq #$1f,d6 ; repeat each case with all incoming CCR bits set
.select:
        cmp.w #4,d4
        bcs .ready
        cmp.w #10,d4
        bcc .remainder
        subq.w #4,d4
        add.w d4,d4
        lea (52,a3),a0
        move.w d7,(a0,d4.w)
        bra .ready
.remainder:
        cmp.w #22,d4
        bcc .speed
        sub.w #10,d4
        cmp.w #6,d4
        bcs .small
        subq.w #6,d4
        muls #12,d7 ; also test out-of-normal-range accumulated fractions
.small: add.w d4,d4
        lea (8,a6),a0
        move.w d7,(a0,d4.w)
        bra .ready
.speed: cmp.w #24,d4
        bcc .boss
        move.w d7,($40,a3)
        bra .ready
.boss:  cmp.w #28,d4
        bcc .ready
        move.w #7,(2,a3)
        move.w #1,(4,a6)
.ready:
        lea (s60_idle_seed,pc),a1
        bsr s60_idle_copy_out
        lea (s60_idle_enable,pc),a0
        clr.w (a0)
        bsr s60_idle_invoke
        and.w #$1f,d1
        lea (s60_idle_ccr,pc),a0
        move.w d1,(a0)
        lea (s60_idle_expected,pc),a1
        bsr s60_idle_copy_out
        bsr s60_idle_restore
        lea (s60_idle_enable,pc),a0
        move.w #1,(a0)
        bsr s60_idle_invoke
        and.w #$1f,d1
        cmp.w (s60_idle_ccr,pc),d1
        beq .actor_compare
        lea (s60_idle_results,pc),a0
        addq.w #1,(10,a0)
.actor_compare:
        lea (s60_idle_expected,pc),a0
        move.l a3,a1
        moveq #$6e/2-1,d0
.actor_word:
        cmpm.w (a0)+,(a1)+
        beq .actor_next
        lea (s60_idle_results,pc),a2
        addq.w #1,(6,a2)
.actor_next: dbf d0,.actor_word
        move.l a6,a1
        moveq #S60_REC/2-1,d0
.record_word:
        cmpm.w (a0)+,(a1)+
        beq .record_next
        lea (s60_idle_results,pc),a2
        addq.w #1,(8,a2)
.record_next: dbf d0,.record_word
        lea (s60_idle_results,pc),a0
        addq.w #1,(4,a0)
        addq.w #1,d5
        cmp.w #64,d5
        bcs .case
        move.l a6,a0
        moveq #S60_REC/2-1,d0
.clear_final: clr.w (a0)+
        dbf d0,.clear_final
        movem.l (sp)+,d0-d7/a0-a6
.done:  rts
        ENDC
        ENDC
