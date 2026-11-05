        IFD VERIFY
        IFD AI_STACK_TEST
; Demonstrate the native state-3 branch's uninitialized local byte dependency.
; Original cases differ only in future local -1(A5); corrected cases restore
; identical RNG input and must consume exactly one native random draw.
s60_ai_stack_results:
        dc.b 'U761'
        dc.w 0
        dc.b 0,0,0,0
        dc.w 0,0 ; expected corrected decision, RNG mismatches
s60_ai_stack_original_rng: ds.b 116
s60_ai_stack_rng: ds.b 116
s60_ai_stack_expected_rng: ds.b 116
s60_ai_stack_actor: ds.b 112
s60_test_ai_stack:
        move.l (s60_ticks,pc),d0
        cmp.l #AI_STACK_TEST,d0
        bne .done
        movem.l d2-d7/a2-a6,-(sp)
        lea ($2434-S60_DATA,a4),a0
        lea (s60_ai_stack_original_rng,pc),a1
        bsr s60_ai_stack_copy_rng
        IFD AI_STACK_LOW
        move.w #4095,d7
        ENDC
.sample:
        lea ($2434-S60_DATA,a4),a0
        lea (s60_ai_stack_rng,pc),a1
        bsr s60_ai_stack_copy_rng
        S60_CALL $116ec
        and.w #255,d0
        IFD AI_STACK_LOW
        cmp.w #2,d0
        bcs .sample_ready
        dbf d7,.sample
        lea (s60_ai_stack_results,pc),a0
        move.w #1,(12,a0) ; bounded search failed: diagnostic must not pass
.sample_ready:
        ENDC
        moveq #3,d1
        cmp.w #2,d0
        bcc .expected
        moveq #5,d1
.expected:
        lea (s60_ai_stack_results,pc),a0
        move.w d1,(10,a0)
        lea ($2434-S60_DATA,a4),a0
        lea (s60_ai_stack_expected_rng,pc),a1
        bsr s60_ai_stack_copy_rng
        moveq #0,d6
.case:
        lea (s60_ai_stack_rng,pc),a0
        lea ($2434-S60_DATA,a4),a1
        bsr s60_ai_stack_copy_rng
        lea (s60_running,pc),a0
        clr.w (a0)
        cmp.w #2,d6
        bcs .setup
        move.w #1,(a0)
.setup:
        lea (s60_ai_stack_actor,pc),a0
        moveq #27,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        lea (s60_ai_stack_actor,pc),a3
        move.w #3,(2,a3)
        move.l #1000,($10,a3)
        move.w #4096,($5e,a3)
        move.b #3,($59,a3)
        move.l a3,-(sp)
        moveq #0,d0
        btst #0,d6
        beq .poison
        moveq #-1,d0
.poison:
        ; JSR and LINK place native A5 eight bytes below this SP.
        move.b d0,(-9,sp)
        S60_CALL $f192
        addq.l #4,sp
        lea (s60_ai_stack_results,pc),a0
        move.b ($59,a3),(6,a0,d6.w)
        addq.w #1,(4,a0)
        cmp.w #2,d6
        bcs .next
        lea ($2434-S60_DATA,a4),a0
        lea (s60_ai_stack_expected_rng,pc),a1
        moveq #28,d2
.check_rng:
        move.l (a0)+,d0
        cmp.l (a1)+,d0
        bne .rng_failed
        dbf d2,.check_rng
        bra .next
.rng_failed:
        lea (s60_ai_stack_results,pc),a0
        addq.w #1,(12,a0)
.next:
        addq.w #1,d6
        cmp.w #4,d6
        bne .case
        lea (s60_ai_stack_original_rng,pc),a0
        lea ($2434-S60_DATA,a4),a1
        bsr s60_ai_stack_copy_rng
        lea (s60_running,pc),a0
        move.w #1,(a0)
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
s60_ai_stack_copy_rng:
        moveq #28,d0
.copy:  move.l (a0)+,(a1)+
        dbf d0,.copy
        rts
        ENDC
        ENDC
