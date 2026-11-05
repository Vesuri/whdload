; Exercise the actual native joystick-neutral braking fragment, privately.
; Compare N fixed substeps with one original 80-unit step for every phase.
        IFD VERIFY
        IFD INPUT_NEUTRAL_TEST
s60_input_neutral_results:
        dc.b 'NI60'
        dc.l 0,0 ; completed cases, endpoint mismatches
        dc.w 0,0,0,0 ; first failing phase, initial, expected, actual
s60_input_neutral_actor: ds.b 112
s60_input_neutral_view: dc.l 0
s60_input_neutral_fragment: ds.b 66
s60_input_neutral_values:
        dc.w 0,1,-1,7,-7,79,-79,80,-80,81,-81,512,-512,32767,-32768
s60_test_input_neutral:
        move.l (s60_ticks,pc),d0
        cmp.l #INPUT_NEUTRAL_TEST,d0
        bne .done
        move.l (s60_input_neutral_results+4,pc),d0
        bne .done
        movem.l d0-d7/a0-a6,-(sp)
        move.w (s60_phase,pc),-(sp)
        lea (s60_input_neutral_actor,pc),a3
        lea (s60_input_neutral_view,pc),a0
        move.l a3,(a0)
        moveq #0,d5 ; starting phase
.phase:
        lea (s60_input_neutral_values,pc),a5
        moveq #14,d6
.case:
        move.w (a5),(56,a3)
        bsr s60_input_neutral_copy
        ; Independent reference: original native full 80-unit braking step.
        lea (s60_input_neutral_fragment,pc),a0
        move.w #$7050,(22,a0)
        move.w #$7450,(50,a0)
        move.w #$7050,(58,a0)
        bsr s60_input_neutral_flush
        bsr s60_input_neutral_fragment
        move.w (56,a3),d3 ; native expected endpoint
        move.w (a5),(56,a3)
        move.w d5,d4
        moveq #S60_SUBSTEPS-1,d7
.step:
        lea (s60_phase,pc),a0
        move.w d4,(a0)
        bsr s60_input_quanta
        bsr s60_input_neutral_copy
        bsr s60_input_neutral_flush
        bsr s60_input_neutral_fragment
        addq.w #1,d4
        cmp.w #S60_SUBSTEPS,d4
        bcs .next_step
        moveq #0,d4
.next_step:
        dbf d7,.step
        lea (s60_input_neutral_results,pc),a0
        cmp.w (56,a3),d3
        beq .passed
        tst.l (8,a0)
        bne .count_error
        move.w d5,(12,a0)
        move.w (a5),(14,a0)
        move.w d3,(16,a0)
        move.w (56,a3),(18,a0)
.count_error:
        addq.l #1,(8,a0)
.passed:
        addq.l #1,(4,a0)
        addq.l #2,a5
        dbf d6,.case
        addq.w #1,d5
        cmp.w #S60_SUBSTEPS,d5
        bcs .phase
        lea (s60_phase,pc),a0
        move.w (sp)+,(a0)
        bsr s60_input_quanta ; restore the live phase's immediates
        movem.l (sp)+,d0-d7/a0-a6
.done:  rts
s60_input_neutral_copy:
        movem.l d0-d2/a0-a2,-(sp)
        move.l (s60_code,pc),a0
        adda.l #$10038,a0
        ; Both absolute view operands must still refer to the same native slot.
        cmp.w #$2079,(a0)
        bne s60_bad
        cmp.w #$2079,(30,a0)
        bne s60_bad
        move.l (2,a0),d0
        cmp.l (32,a0),d0
        bne s60_bad
        cmp.l #$30280038,(6,a0)
        bne s60_bad
        cmp.l #$95680038,(52,a0)
        bne s60_bad
        cmp.l #$d1680038,(60,a0)
        bne s60_bad
        lea (s60_input_neutral_fragment,pc),a1
        moveq #15,d0
.copy:  move.l (a0)+,(a1)+
        dbf d0,.copy
        move.w #$4e75,(a1)
        lea (s60_input_neutral_fragment,pc),a1
        lea (s60_input_neutral_view,pc),a2
        move.l a2,(2,a1)
        move.l a2,(32,a1)
        movem.l (sp)+,d0-d2/a0-a2
        rts
s60_input_neutral_flush:
        movem.l d0-d2/a0-a2,-(sp)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d2/a0-a2
        rts
        ENDC
        ENDC
