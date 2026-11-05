; Independent per-actor contact clocks. Immediate impacts are not patched.
; Record longs 68..84 hold last effect ticks; byte 88 has validity bits 0..4.
s60_contact_install:
        move.l (s60_code,pc),a1
        cmp.l #$61000586,($373a,a1)
        bne s60_bad
        cmp.w #$544f,($373e,a1)
        bne s60_bad
        cmp.l #$61000496,($382a,a1)
        bne s60_bad
        cmp.w #$544f,($382e,a1)
        bne s60_bad
        cmp.l #$6100095a,($35a8,a1)
        bne s60_bad
        cmp.w #$5c4f,($35ac,a1)
        bne s60_bad
        cmp.l #$61000650,($38b2,a1)
        bne s60_bad
        cmp.w #$5c4f,($38b6,a1)
        bne s60_bad
        cmp.l #$4eba63f4,($3590,a1)
        bne s60_bad
        cmp.w #$584f,($3594,a1)
        bne s60_bad
        cmp.l #$4eba04d6,($3cb8,a1)
        bne s60_bad
        cmp.w #$584f,($3cbc,a1)
        bne s60_bad
        lea (s60_contact_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_contact_patches:
        PL_START
        PL_PS $373a,s60_contact_player_first
        PL_PS $382a,s60_contact_player_second
        PL_PS $3590,s60_contact_shield_sound
        PL_PS $35a8,s60_contact_shield
        PL_PS $38b2,s60_contact_actor
        PL_PS $3cb8,s60_contact_boss
        PL_END
; d1 = path 0..4, bit 7 = preview only; a3 = actor; d0 = due.
; Unsigned elapsed subtraction tolerates the 32-bit tick counter wrapping.
s60_contact_due:
        movem.l d1-d2/a6,-(sp)
        move.w (s60_running,pc),d0
        beq .yes
        bsr s60_motion_record
        move.w d1,d2
        and.w #7,d2
        lsl.w #2,d2
        add.w #68,d2
        btst d1,(88,a6)
        beq .accept
        move.l (s60_ticks,pc),d0
        sub.l (a6,d2.w),d0
        cmp.l #S60_LEGACY_DIV,d0
        bcs .no
.accept:
        btst #7,d1
        bne .yes
        bset d1,(88,a6)
        move.l (s60_ticks,pc),(a6,d2.w)
.yes:   moveq #1,d0
        bra .done
.no:    moveq #0,d0
.done:  movem.l (sp)+,d1-d2/a6
        rts
s60_contact_player_first:
        moveq #0,d1
        bra s60_contact_player
s60_contact_player_second:
        moveq #1,d1
s60_contact_player:
        bsr s60_contact_due
        tst.w d0
        beq .return
        move.w (4,sp),-(sp)
        S60_CALL $3cc2
        addq.l #2,sp
.return:
        ; Each six-byte hook includes the native two-byte argument cleanup.
        move.l (sp),(2,sp)
        addq.l #2,sp
        rts
s60_contact_shield:
        moveq #2,d1
        bra s60_contact_health
s60_contact_actor:
        moveq #3,d1
s60_contact_health:
        bsr s60_contact_due
        tst.w d0
        beq .return ; zero means no kill, so the caller must not award score
        move.w (8,sp),-(sp)
        move.l (6,sp),-(sp)
        S60_CALL $3f04
        addq.l #6,sp
.return:
        move.l (sp),(6,sp)
        addq.l #6,sp
        rts

s60_contact_shield_sound:
        move.w #130,d1 ; preview the shield clock without consuming its hit
        bsr s60_contact_due
        tst.w d0
        beq .return
        IFD VERIFY
        IFD CONTACT_TEST
        lea (s60_contact_results,pc),a0
        tst.w (12,a0)
        beq .sound
        addq.w #1,(10,a0)
.sound:
        ENDC
        ENDC
        move.l (4,sp),-(sp)
        S60_CALL $9986
        addq.l #4,sp
.return:
        move.l (sp),(4,sp)
        addq.l #4,sp
        rts

; The collision callback is independent of the five-Hz boss AI dispatcher.
s60_contact_boss:
        moveq #4,d1
        bsr s60_contact_due
        tst.w d0
        beq .return
        move.l (4,sp),-(sp)
        S60_CALL $112cc
        addq.l #4,sp
.return:
        move.l (sp),(4,sp)
        addq.l #4,sp
        rts
