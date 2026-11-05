; Three native ejection stages share the cinematic clock. Resource changes,
; camera cuts and cleanup stay at the original stage boundaries.
ejection_loop:
        bsr.w intro_start
        bsr.w ejection_spin_sample
.loop:
        bsr.w intro_due
        move.w d0,d5
.ticks:
        tst.w d5
        beq.s .draw
        cmpi.w #2,d7
        bne.s .world
        bsr.w ejection_effect
.world:
        bsr.w intro_world
        bsr.w ejection_spin_sample
        tst.w d7
        bne.s .later
        bsr.w ejection_step0
        bra.s .next
.later:
        cmpi.w #1,d7
        bne.s .explosion
        add.w d3,d6
        bra.s .next
.explosion:
        cmpi.w #10,d2
        bne.s .next
        bsr.w ejection_explode
.next:
        addq.w #1,d2
        cmpi.w #2,d7
        beq.s .long
        cmpi.w #10,d2
        bra.s .limit
.long:
        cmpi.w #200,d2
.limit:
        bhs.s .done
        subq.w #1,d5
        bra.s .ticks
.draw:
        bsr.w intro_draw
        bsr.w ejection_overlay
        bsr.w intro_finish
        bsr.w modal_input
        tst.w MODAL_ABORT(a4)
        beq.w .loop
.done:
        bsr.w intro_stop
        rts

; Only bitmap coordinates are sampled; the native script registers are restored.
; D2 counts completed ticks; native frame selection remains discrete.
ejection_overlay:
        movem.l d2-d6,-(sp)
        lea ejection_overlay(pc),a0
        adda.l #MODAL_CLOCK-ejection_overlay,a0
        move.l 4(a0),d0
        lea ejection_overlay(pc),a0
        adda.l #MODAL_HZ-ejection_overlay,a0
        move.w 2(a0),d1
        cmp.w d1,d0
        blo.s .fraction
        move.w d1,d0
        subq.w #1,d0
.fraction:
        mulu.w d3,d0
        divu.w d1,d0
        tst.w d7
        bne.s .later
        cmpi.w #1,d2
        ble.s .seat
        sub.w d0,d4
.seat:
        bsr.w ejection_draw0
        bra.s .done
.later:
        cmpi.w #1,d7
        bne.s .pilot
        add.w d0,d6
        bsr.w ejection_draw1
        bra.s .done
.pilot:
        bsr.w ejection_draw2
.done:
        movem.l (sp)+,d2-d6
        rts

; The pilot's four-unit tumble is an explicit script call, outside the native
; angular-rate arrays. Add it to the fresh render snapshot, never game state.
ejection_spin_sample:
        cmpi.w #2,d7
        bne.s .done
        movem.l d0/a0,-(sp)
        move.w EJECTION_SLOT(a4),d0
        cmpi.w #61,d0
        bhs.s .restore
        add.w d0,d0
        lea ejection_spin_sample(pc),a0
        adda.l #timing_scene_angles-ejection_spin_sample,a0
        adda.w d0,a0
        addq.w #4,(a0)
        ; Native view 10 copies the pilot basis into camera slot 61. Its
        ; own angular-rate words are zero, so supply the same script tumble.
        cmpi.w #10,EJECTION_VIEW(a4)
        bne.s .restore
        move.w EJECTION_SLOT(a4),d0
        cmp.w EJECTION_SUBJECT(a4),d0
        bne.s .restore
        lea ejection_spin_sample(pc),a0
        adda.l #timing_scene_angles+122-ejection_spin_sample,a0
        addq.w #4,(a0)
.restore:
        movem.l (sp)+,d0/a0
.done:
        rts
