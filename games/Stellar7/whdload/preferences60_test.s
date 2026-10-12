; Real preferences + nested native pause dialog. Only the input polls are
; supplied; native drawing, modal wrappers and return paths remain active.
        IFD VERIFY
        IFD PREFERENCES_TEST
        IFD PREFERENCES_SEQUENCE
        IFD PREFERENCES_CHOICE
        FAIL "PREFERENCES_SEQUENCE and PREFERENCES_CHOICE are separate fixtures"
        ENDC
        ENDC
        IFD PREFERENCES_CHOICE
        IFLT PREFERENCES_CHOICE-1
        FAIL "PREFERENCES_CHOICE must be 1..4"
        ENDC
        IFGT PREFERENCES_CHOICE-4
        FAIL "PREFERENCES_CHOICE must be 1..4"
        ENDC
        ENDC
s60_preferences_results:
        IFD PREFERENCES_SEQUENCE
        dc.b 'PF62'
        ELSE
        IFD PREFERENCES_CHOICE
        dc.b 'PF61'
        ELSE
        dc.b 'PF60'
        ENDC
        ENDC
        dc.w 0,0 ; stage, errors
        ds.l 11 ; tick, entry field, outer last/credit, first poll, nested start/end,
                ; return field/last/credit/tick
        ds.w 6 ; resumes before/after, nested depth/rendering, return depth/rendering
        ds.l 2 ; nested last/credit after return
        IFD PREFERENCES_CHOICE
        dc.w 0,0,0,PREFERENCES_CHOICE ; selections, before, after, option
        ENDC
        IFD PREFERENCES_SEQUENCE
        dc.w 0 ; number of native toggle selections supplied
        ds.w 9*4 ; initial settings and settings after each of eight toggles
        ENDC
s60_test_preferences:
        move.l (s60_ticks,pc),d0
        cmp.l #PREFERENCES_TEST,d0
        bne .done
        move.w (s60_preferences_results+4,pc),d0
        bne .done
        movem.l d0-d7/a0-a6,-(sp)
        IFNE S60_SUBSTEPS-12
        ; Lower rates can reach this tick with zero credit. Accrue one real
        ; tick of field time before the modal wrapper samples the clock;
        ; never inject private debt. N12 retains its byte-identical fixture.
        moveq #0,d2
        move.w (s60_field_hz,pc),d2
        add.w #S60_RATE-1,d2
        divu #S60_RATE,d2
        and.l #$ffff,d2
        move.l ($24a8-S60_DATA,a4),d1
.debt_wait:
        move.l ($24a8-S60_DATA,a4),d0
        sub.l d1,d0
        cmp.l d2,d0
        bcs .debt_wait
        ENDC
        lea (s60_preferences_results,pc),a0
        move.w #1,(4,a0)
        IFD PREFERENCES_CHOICE
        move.w ($1e72+PREFERENCES_CHOICE*2-S60_DATA,a4),(74,a0)
        ENDC
        move.l (s60_ticks,pc),(8,a0)
        move.l ($24a8-S60_DATA,a4),(12,a0)
        move.w (s60_modal_resumes,pc),(52,a0)
        S60_CALL $3148 ; native input-dispatch Forbid
        S60_CALL $d3a8 ; actual preferences entry, including its modal wrapper
        S60_CALL $312c ; native Permit
        lea (s60_preferences_results,pc),a0
        IFD PREFERENCES_CHOICE
        move.w ($1e72+PREFERENCES_CHOICE*2-S60_DATA,a4),(76,a0)
        ENDC
        move.l ($24a8-S60_DATA,a4),(36,a0)
        move.l (s60_last,pc),(40,a0)
        move.l (s60_credit,pc),(44,a0)
        move.l (s60_ticks,pc),(48,a0)
        move.w (s60_modal_resumes,pc),(54,a0)
        move.w (s60_modal_depth,pc),(60,a0)
        move.w (s60_rendering,pc),(62,a0)
        cmp.w #2,(4,a0)
        beq .returned
        addq.w #1,(6,a0)
.returned:
        move.w #3,(4,a0)
        movem.l (sp)+,d0-d7/a0-a6
.done:  rts
s60_test_preferences_poll:
        movem.l d1-d7/a0-a6,-(sp)
        lea (s60_preferences_results,pc),a0
        tst.l (24,a0)
        bne .elapsed
        move.l ($24a8-S60_DATA,a4),(24,a0)
        move.l (s60_last,pc),(16,a0)
        move.l (s60_credit,pc),(20,a0)
.elapsed:
        move.l ($24a8-S60_DATA,a4),d0
        sub.l (24,a0),d0
        cmp.w #1,(4,a0)
        bne .outer_wait
        cmp.l #20,d0
        bcs .wait
        move.l ($24a8-S60_DATA,a4),(28,a0)
        move.l ($24a8-S60_DATA,a4),d0
        add.l #30,d0
        lea (s60_test_pause_deadline,pc),a1
        move.l d0,(a1)
        S60_CALL $10268 ; native P handler enters a real nested dialog
        lea (s60_preferences_results,pc),a0
        move.l ($24a8-S60_DATA,a4),(32,a0)
        move.w (s60_modal_depth,pc),(56,a0)
        move.w (s60_rendering,pc),(58,a0)
        move.l (s60_last,pc),(64,a0)
        move.l (s60_credit,pc),(68,a0)
        move.w #2,(4,a0)
        bra .wait
.outer_wait:
        cmp.l #90,d0
        bcs .wait
        IFD PREFERENCES_SEQUENCE
        ; Observe all four settings before supplying the next button. Native
        ; handlers alone change settings: toggle each off, then each back on.
        moveq #0,d1
        move.w (72,a0),d1
        move.w d1,d2
        lsl.w #3,d2
        lea (74,a0),a1
        adda.w d2,a1
        move.l ($1e74-S60_DATA,a4),(a1)
        move.l ($1e78-S60_DATA,a4),(4,a1)
        cmp.w #8,d1
        bcc .sequence_done
        move.w d1,d0
        and.w #3,d0
        addq.w #2,d0 ; native buttons 2..5, twice
        addq.w #1,(72,a0)
        bra .return
.sequence_done:
        ENDC
        IFD PREFERENCES_CHOICE
        tst.w (72,a0)
        bne .selected
        addq.w #1,(72,a0)
        moveq #PREFERENCES_CHOICE+1,d0 ; select native toggle; no setting writes
        bra .return
.selected:
        ENDC
        moveq #6,d0 ; native preferences Done button
        bra .return
.wait:  moveq #0,d0
.return:
        movem.l (sp)+,d1-d7/a0-a6
        move.l d0,d7 ; displaced MOVE.L after the native input call
        rts
        ENDC
        ENDC
