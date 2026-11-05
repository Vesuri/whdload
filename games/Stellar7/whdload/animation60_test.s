        IFD VERIFY
        IFD ANIMATION_TEST
S60_ANIM_STAGGER SET (S60_SUBSTEPS-1)/2
        IFEQ S60_SUBSTEPS-2
S60_ANIM_STAGGER SET 1
        ENDC
; Two mesh animations, two explosion lifetimes and four frame oscillators.
; Four native intervals versus 48 updates, with duplicate and render callbacks.
s60_animation_results:
        dc.b 'A762'
        dc.w 0,0,0,0 ; completed, failed cases, refresh errors, independence errors
        ds.b 8*8
s60_anim_case_error: dc.w 0
s60_anim_actor: ds.b 368 ; actor plus maximum byte-indexed animation array
s60_anim_second: ds.b 368
s60_anim_expected: ds.b 4*368
s60_anim_gate:
        movem.l d0/a0/a2,-(sp)
        move.l (s60_code,pc),a0
        tst.w d0
        beq .restore
        cmp.w #$3f07,($433c,a0)
        bne s60_bad
        cmp.w #$4cdf,($3a4e,a0)
        bne s60_bad
        move.w #$4e75,($433c,a0)
        move.w #$4e75,($3a4e,a0)
        adda.l #$8000,a0
        cmp.w #$41ea,($12c2,a0)
        bne s60_bad
        move.w #$4e75,($12c2,a0)
        cmp.w #$4ef9,($1492,a0)
        bne s60_bad
        move.w #$4e75,($1492,a0)
        bra .flush
.restore:
        move.w #$3f07,($433c,a0)
        move.w #$4cdf,($3a4e,a0)
        adda.l #$8000,a0
        move.w #$41ea,($12c2,a0)
        move.w #$4ef9,($1492,a0)
.flush:
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0/a0/a2
        rts
s60_anim_start:
        cmp.w #4,d5
        bge .oscillator
        cmp.w #2,d5
        bge .explosion
        S60_CALL $4334 ; actual eight-byte initializer hook, temporary RTS after it
        rts
.explosion:
        move.l a2,-(sp)
        move.l a3,a2
        S60_CALL $3a46
        move.l (sp)+,a2
        rts
.oscillator:
        move.l a2,-(sp)
        move.l a3,a2
        S60_CALL $92b6
        move.l (sp)+,a2
        rts
s60_anim_setup:
        lea (s60_anim_actor,pc),a3
        move.l a3,a0
        moveq #91,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        lea (112,a3),a0
        move.l a0,($1e,a3)
        cmp.w #4,d5
        bge .oscillator
        move.w #11,(2,a3)
        tst.w d5
        beq .start
        cmp.w #1,d5
        bne .explosion
        move.w #41,(2,a3)
        move.b #2,($56,a3)
        move.b #1,($57,a3)
        bra .start
.explosion:
        move.w #-1,(2,a3)
        move.b #1,($55,a3)
        move.b #6,($58,a3)
        cmp.w #3,d5
        bne .start
        move.b #4,($55,a3)
.start: bsr s60_anim_start
        rts
.oscillator:
        move.w #25,(2,a3)
        lea ($56,a3),a0
        move.l a0,($1e,a3)
        move.l (s60_code,pc),a0
        adda.l #$394c,a0
        move.l a0,($1a,a3) ; non-null marker for the isolated dispatcher
        bsr s60_anim_start
        cmp.w #4,d5
        beq .osc_done
        cmp.w #5,d5
        bne .upper
        clr.b ($56,a3)
        move.b #-1,($59,a3)
        bra .osc_done
.upper: move.b #3,($56,a3)
        cmp.w #6,d5
        beq .osc_done
        move.b #-128,($56,a3)
        move.b #-1,($59,a3)
.osc_done:
        rts
s60_anim_native:
        tst.l ($1a,a3)
        beq .done
        clr.w -(sp)
        move.l a3,-(sp)
        cmp.w #4,d5
        bge .oscillator
        cmp.w #2,d5
        bge .explosion
        bsr s60_animation_native
        bra .return
.explosion:
        bsr s60_explosion_native
.return:
        addq.l #6,sp
.done:  rts
.oscillator:
        bsr s60_oscillator_native
        bra .return
s60_anim_replacement:
        tst.l ($1a,a3)
        beq .done
        clr.w -(sp)
        move.l a3,-(sp)
        cmp.w #4,d5
        bge .oscillator
        cmp.w #2,d5
        bge .explosion
        S60_CALL $42b0
        bra .return
.explosion:
        S60_CALL $397e
.return:
        addq.l #6,sp
.done:  rts
.oscillator:
        S60_CALL $394c
        bra .return
s60_anim_error:
        lea (s60_anim_case_error,pc),a0
        move.w #1,(a0)
        rts
s60_anim_check:
        lea (s60_anim_actor,pc),a0
        move.l a2,a1
        moveq #91,d0
.loop:  move.l (a0)+,d1
        cmp.l (a1)+,d1
        bne s60_anim_error
        dbf d0,.loop
        rts
s60_test_animation:
        move.l (s60_ticks,pc),d0
        cmp.l #ANIMATION_TEST,d0
        bne .done
        move.w (s60_animation_results+4,pc),d0
        bne .done ; one fixture pass per boot, including after death/retry
        movem.l d2-d7/a2-a6,-(sp)
        move.l (s60_ticks,pc),-(sp)
        move.w (s60_logic,pc),-(sp)
        move.w ($1e50-S60_DATA,a4),-(sp)
        move.w ($291e-S60_DATA,a4),-(sp)
        lea (s60_logic,pc),a0
        clr.w (a0) ; must work independently of global native phase
        clr.b ($1e51-S60_DATA,a4)
        moveq #1,d0
        bsr s60_anim_gate
        moveq #0,d5
.case:
        lea (s60_anim_case_error,pc),a0
        clr.w (a0)
        bsr s60_anim_setup
        lea (s60_anim_expected,pc),a2
        moveq #3,d6
.native:
        bsr s60_anim_native
        move.l a3,a0
        moveq #91,d0
.copy:  move.l (a0)+,(a2)+
        dbf d0,.copy
        dbf d6,.native
        bsr s60_anim_setup
        bsr s60_motion_record
        lea (s60_ticks,pc),a0
        move.w d5,d0
        mulu #5,d0
        add.l #203,d0
        cmp.w #3,d5
        bne .set_tick
        moveq #-8,d0 ; wraparound within the first interval
.set_tick:
        move.l d0,(a0)
        lea (s60_anim_expected,pc),a2
        moveq #0,d6
.period:
        moveq #0,d7
.tick:
        bsr s60_anim_replacement
        bsr s60_anim_replacement ; duplicate in same simulation tick
        lea (s60_rendering,pc),a0
        move.w #1,(a0)
        bsr s60_anim_replacement
        lea (s60_rendering,pc),a0
        clr.w (a0)
        bsr s60_anim_check
        lea (s60_ticks,pc),a0
        addq.l #1,(a0)
        addq.w #1,d7
        cmp.w #S60_SUBSTEPS,d7
        bne .tick
        adda.w #368,a2
        addq.w #1,d6
        cmp.w #4,d6
        bne .period
        lea (s60_animation_results,pc),a0
        addq.w #1,(4,a0)
        move.w (s60_anim_case_error,pc),d0
        add.w d0,(6,a0)
        lea (12,a0),a1
        move.w d5,d1
        lsl.w #3,d1
        adda.w d1,a1
        move.w (2,a3),(a1)
        move.w d0,(2,a1)
        move.w ($56,a3),(4,a1)
        move.w ($54,a3),(6,a1)
        tst.w d5
        bne .forget
        ; Reassign the same callback five ticks after an immediate first call.
        ; Without initializer reset this second event would remain blocked.
        bsr s60_anim_setup
        lea (s60_ticks,pc),a0
        moveq #10,d0
        move.l d0,(a0)
        bsr s60_anim_replacement
        lea (s60_ticks,pc),a0
        IFNE S60_ANIM_STAGGER
        addq.l #S60_ANIM_STAGGER,(a0)
        ENDC
        bsr s60_anim_replacement
        lea (s60_anim_expected,pc),a2
        lea (s60_anim_case_error,pc),a0
        clr.w (a0)
        bsr s60_anim_check
        bsr s60_anim_start
        bsr s60_anim_replacement
        adda.w #368,a2
        bsr s60_anim_check
        cmp.l #10+S60_ANIM_STAGGER,(132,a6)
        beq .refresh_ok
        bsr s60_anim_error
.refresh_ok:
        lea (s60_animation_results,pc),a0
        move.w (s60_anim_case_error,pc),(8,a0)
        bsr s60_anim_independence
.forget:
        move.l a6,a0
        moveq #(S60_REC/4)-1,d0
.clear_record:
        clr.l (a0)+
        dbf d0,.clear_record
        addq.w #1,d5
        cmp.w #8,d5
        bne .case
        bsr s60_anim_osc_refresh
        moveq #0,d0
        bsr s60_anim_gate
        move.w (sp)+,($291e-S60_DATA,a4)
        move.w (sp)+,($1e50-S60_DATA,a4)
        lea (s60_logic,pc),a0
        move.w (sp)+,(a0)
        lea (s60_ticks,pc),a0
        move.l (sp)+,(a0)
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
s60_anim_independence:
        bsr s60_anim_setup
        lea (s60_anim_case_error,pc),a0
        clr.w (a0)
        move.l a3,a0
        lea (s60_anim_second,pc),a1
        moveq #91,d0
.copy:  move.l (a0)+,(a1)+
        dbf d0,.copy
        lea (s60_anim_second,pc),a3
        lea (112,a3),a0
        move.l a0,($1e,a3)
        bsr s60_anim_start
        lea (s60_ticks,pc),a0
        move.l #10,(a0)
        lea (s60_anim_actor,pc),a3
        bsr s60_anim_replacement
        lea (s60_ticks,pc),a0
        move.l #10+S60_ANIM_STAGGER,(a0)
        lea (s60_anim_second,pc),a3
        bsr s60_anim_replacement
        lea (s60_ticks,pc),a0
        move.l #10+S60_SUBSTEPS,(a0)
        lea (s60_anim_actor,pc),a3
        bsr s60_anim_replacement
        cmp.b #2,(112,a3)
        beq .first_ok
        bsr s60_anim_error
.first_ok:
        bsr s60_motion_record
        cmp.l #10+S60_SUBSTEPS,(132,a6)
        beq .first_clock_ok
        bsr s60_anim_error
.first_clock_ok:
        lea (s60_anim_second,pc),a3
        bsr s60_anim_replacement
        IFEQ S60_SUBSTEPS-1
        cmp.b #2,(112,a3) ; at N=1 both independent clocks are due this tick
        ELSE
        cmp.b #1,(112,a3)
        ENDC
        beq .second_ok
        bsr s60_anim_error
.second_ok:
        bsr s60_motion_record
        IFEQ S60_SUBSTEPS-1
        cmp.l #10+S60_SUBSTEPS,(132,a6)
        ELSE
        cmp.l #10+S60_ANIM_STAGGER,(132,a6)
        ENDC
        beq .second_clock_ok
        bsr s60_anim_error
.second_clock_ok:
        lea (s60_ticks,pc),a0
        move.l #10+S60_SUBSTEPS+S60_ANIM_STAGGER,(a0)
        bsr s60_anim_replacement
        cmp.b #2,(112,a3)
        beq .last_ok
        bsr s60_anim_error
.last_ok:
        cmp.l #10+S60_SUBSTEPS+S60_ANIM_STAGGER,(132,a6)
        beq .last_clock_ok
        bsr s60_anim_error
.last_clock_ok:
        move.l a6,a0
        moveq #(S60_REC/4)-1,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        lea (s60_animation_results,pc),a0
        move.w (s60_anim_case_error,pc),(10,a0)
        lea (s60_anim_actor,pc),a3
        bsr s60_motion_record
        rts
s60_anim_osc_refresh:
        moveq #4,d5
        bsr s60_anim_setup
        bsr s60_motion_record
        lea (s60_anim_case_error,pc),a0
        clr.w (a0)
        lea (s60_ticks,pc),a0
        move.l #10,(a0)
        bsr s60_anim_replacement
        lea (s60_ticks,pc),a0
        IFNE S60_ANIM_STAGGER
        addq.l #S60_ANIM_STAGGER,(a0)
        ENDC
        bsr s60_anim_replacement
        cmp.b #3,($56,a3)
        bne .error
        cmp.l #10,(140,a6)
        bne .error
        move.l #77,(132,a6)
        bset #1,(136,a6) ; another clock must survive oscillator restart
        bsr s60_anim_start
        cmp.b #2,($56,a3)
        bne .error
        bsr s60_anim_replacement
        cmp.b #3,($56,a3)
        bne .error
        cmp.l #10+S60_ANIM_STAGGER,(140,a6)
        bne .error
        cmp.l #77,(132,a6)
        bne .error
        btst #1,(136,a6)
        bne .checked
.error: bsr s60_anim_error
.checked:
        lea (s60_animation_results,pc),a0
        move.w (s60_anim_case_error,pc),d0
        add.w d0,(8,a0)
        clr.l -(sp) ; both native global oscillator pointers may be null
        S60_CALL $394c
        addq.l #4,sp
        move.l a6,a0
        moveq #(S60_REC/4)-1,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        rts
        ENDC
        ENDC
