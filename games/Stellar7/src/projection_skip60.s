; Omit unused geometry only in simulation, preserving callbacks and final scratch.
        IFNE PROJECT_SKIP
s60_project_actor_native: ds.b 14
s60_project_skip_install:
        move.l (s60_code,pc),a1
        move.l a1,a0
        adda.l #$12adc,a0
        cmp.l #$206cdd90,(a0)
        bne s60_bad
        cmp.l #$b7e80002,(4,a0)
        bne s60_bad
        cmp.l #$6700014a,(8,a0)
        bne s60_bad
        cmp.l #$202b001a,($120,a0)
        bne s60_bad
        adda.w #12,a0
        lea (s60_project_actor_native,pc),a3
        move.l #$202b0008,d0
        move.l #$90acddc2,d1
        bsr s60_draw_trampoline
        lea (s60_project_skip_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_project_skip_patches:
        PL_START
        PL_P $12ae8,s60_project_actor
        PL_NOP $12aee,2
        PL_END
s60_project_actor:
        IFD VERIFY
        IFD PROJECT_TEST
        bsr s60_test_project
        ENDC
        ENDC
        move.w (s60_running,pc),d0
        beq .native
        move.w (s60_rendering,pc),d0
        bne .native
        btst #3,(a3)
        bne .native ; actor visibility and projected coordinates must update
        ; Keep the final list entry's geometry, restoring all shared geometry
        ; scratch for post callbacks and subsequent consumers. If it is the
        ; view actor (which native iteration skips), retain every calculation.
        move.w d7,d0
        subq.w #1,d0
        cmp.w d6,d0
        ble .native
        sub.w d6,d0
        lsl.w #2,d0
        move.l (a2,d0.w),d1
        cmp.l (2,a0),d1 ; native $12adc left the current view pointer in A0
        beq .native
        move.l (26,a3),d0
        beq .skip
        sub.l (s60_code,pc),d0
        cmp.l #$42b0,d0
        bne .native ; unknown callbacks may consume projection scratch
        ; $42b0 updates actor animation only; it does not read projection data.
.skip:  S60_TAIL $12bfc ; retain native callback ordering and draw suppression
.native:
        bra s60_project_actor_native
        ENDC
