; Exclude actual modal dialogs/preferences, not every native Forbid/Permit pair.
; Ordinary input, collision handling and rendering remain charged to the clock.
s60_dialog_native: ds.b 14
s60_preferences_native: ds.b 12
s60_modal_install:
        move.l (s60_code,pc),a1
        move.l a1,a0
        adda.l #$df32,a0
        lea (s60_dialog_native,pc),a3
        move.l #$4e55fffc,d0
        move.l #$48e72330,d1
        bsr s60_draw_trampoline
        move.l a1,a0
        adda.l #$d3a8,a0
        cmp.l #$48e70700,(a0)
        bne s60_bad
        cmp.w #$7c01,(4,a0)
        bne s60_bad
        lea (s60_preferences_native,pc),a3
        move.l (a0)+,(a3)+
        move.w (a0)+,(a3)+
        move.w #$4ef9,(a3)+
        move.l a0,(a3)
        IFD VERIFY
        IFD S60_MODAL_TEST
        move.l a1,a0
        adda.l #$e1f6,a0
        cmp.l #$4ebac856,(a0)
        bne s60_bad
        cmp.w #$2e00,(4,a0)
        bne s60_bad
        ENDC
        ENDC
        IFD VERIFY
        IFD PREFERENCES_TEST
        move.l a1,a0
        adda.l #$d43a,a0
        cmp.l #$4ebad612,(a0)
        bne s60_bad
        cmp.w #$2e00,(4,a0)
        bne s60_bad
        ENDC
        ENDC
        lea (s60_modal_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_modal_patches:
        PL_START
        PL_P $df32,s60_dialog
        PL_NOP $df38,2
        PL_P $d3a8,s60_preferences
        IFD VERIFY
        IFD PREFERENCES_TEST
        PL_PS $d43a,s60_test_preferences_poll
        ENDC
        ENDC
        IFD VERIFY
        IFD S60_MODAL_TEST
        PL_PS $e1f6,s60_test_modal_poll
        ENDC
        ENDC
        PL_END
s60_dialog:
        IFD VERIFY
        IFD DEATH_TEST
        bsr s60_test_death_dialog
        ENDC
        ENDC
        move.w (s60_running,pc),d0
        beq s60_dialog_native
        move.w (s60_modal_depth,pc),d0
        bne s60_dialog_native
        movem.l d2/a2,-(sp)
        lea (s60_last,pc),a2
        bsr s60_history_lock
        bsr s60_clock ; retain active time accrued before entering the modal
        move.w #1,(s60_modal_depth-s60_last,a2)
        IFD VERIFY
        IFD PAUSE_TEST
        lea (s60_test_pause_observation+4,pc),a0
        move.l ($24a8-S60_DATA,a4),(a0)
        ENDC
        ENDC
        bsr s60_history_unlock
        move.w (s60_rendering-s60_last,a2),d2
        move.w #1,(s60_rendering-s60_last,a2)
        ; Native dialog takes three long arguments. Copy in reverse order.
        move.l (20,sp),-(sp)
        move.l (20,sp),-(sp)
        move.l (20,sp),-(sp)
        bsr s60_dialog_native
        lea (12,sp),sp
        bra s60_modal_return
s60_preferences:
        move.w (s60_running,pc),d0
        beq s60_preferences_native
        move.w (s60_modal_depth,pc),d0
        bne s60_preferences_native
        movem.l d2/a2,-(sp)
        lea (s60_last,pc),a2
        bsr s60_history_lock
        bsr s60_clock ; retain active time accrued before entering the modal
        move.w #1,(s60_modal_depth-s60_last,a2)
        IFD VERIFY
        IFD PAUSE_TEST
        lea (s60_test_pause_observation+4,pc),a0
        move.l ($24a8-S60_DATA,a4),(a0)
        ENDC
        ENDC
        bsr s60_history_unlock
        move.w (s60_rendering-s60_last,a2),d2
        move.w #1,(s60_rendering-s60_last,a2)
        bsr s60_preferences_native
s60_modal_return:
        bsr s60_history_lock
        IFD VERIFY
        IFD PAUSE_TEST
        lea (s60_test_pause_observation+8,pc),a0
        move.l ($24a8-S60_DATA,a4),(a0)
        ENDC
        ENDC
        move.w d2,(s60_rendering-s60_last,a2)
        move.l ($24a8-S60_DATA,a4),(a2)
        IFD VERIFY
        IFD PREFERENCES_TEST
        IFD PREFERENCES_BAD_CREDIT
        clr.l (s60_credit-s60_last,a2) ; negative control: discard owed updates
        ENDC
        ENDC
        ENDC
        ; Preserve pre-pause credit. Only the interval inside the outer modal
        ; is excluded by moving last_field forward without adding that time.
        clr.w (s60_modal_depth-s60_last,a2)
        addq.w #1,(s60_modal_resumes-s60_last,a2)
        bsr s60_history_unlock
        movem.l (sp)+,d2/a2
        rts

        IFD VERIFY
        IFD S60_MODAL_TEST
s60_test_pause_deadline: dc.l 0
        IFD PAUSE_TEST
s60_test_pause_observation:
        dc.b 'PH60'
        dc.l 0,0 ; independently observed native dialog entry/return fields
        ENDC
        IFD PAUSE_TEST
s60_test_pause:
        move.l (s60_ticks,pc),d0
        cmp.l #PAUSE_TEST,d0
        bne .done
        move.l ($24a8-S60_DATA,a4),d0
        IFND PAUSE_FIELDS
PAUSE_FIELDS EQU 60
        ENDC
        add.l #PAUSE_FIELDS,d0
        lea (s60_test_pause_deadline,pc),a0
        move.l d0,(a0)
        S60_CALL $3148 ; native input dispatcher enters Forbid
        S60_CALL $10268 ; native P handler and real pause dialog
        S60_CALL $312c ; native dispatcher resumes with Permit
.done:  rts
        ENDC
s60_test_modal_poll:
        IFD DEATH_TEST
        move.w (s60_death_results+4,pc),d0
        cmp.w #1,d0
        bne .pause
        move.w (s60_death_results+64,pc),d0
        beq .pause
        bra s60_test_death_poll
.pause:
        ENDC
        move.l (s60_test_pause_deadline,pc),d0
        beq .native
        cmp.l ($24a8-S60_DATA,a4),d0
        bhi .wait
        lea (s60_test_pause_deadline,pc),a0
        clr.l (a0)
        moveq #1,d0 ; select the native dialog's Continue button
        move.l d0,d7
        rts
.wait:  moveq #0,d0
        move.l d0,d7
        rts
.native:
        S60_CALL $aa4e
        move.l d0,d7
        rts
        ENDC
        ENDC

        INCLUDE preferences60_test.s
