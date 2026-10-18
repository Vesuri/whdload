; Enhanced modal scenes: one animation step per tenth of a second.
; Native room loops consume actions; cursor polling also runs between ticks.
; Each room rebases after setup and returns from dialogs; load time is never
; animation debt.
modal_room_begin:
        movem.l d0-d1/a0,-(sp)
        bsr.w timing_rate
        lea modal_hz(pc),a0
        move.w d0,(a0)
        divu.w #10,d0
        move.l MODAL_FIELD(a4),d1
        sub.l d0,d1
        lea modal_room_cursor(pc),a0
        move.l d1,(a0)
        lea modal_room_input_field(pc),a0
        move.l MODAL_FIELD(a4),(a0)
        lea modal_room_input_phase(pc),a0
        move.w modal_hz(pc),(a0)
        lea modal_label_previous(pc),a0
        clr.l (a0)
        lea modal_room_result(pc),a0
        move.w #-1,(a0)
        movem.l (sp)+,d0-d1/a0
        rts
modal_room_wait:
        movem.l d0-d2/a0,-(sp)
        moveq #0,d2
        move.w modal_hz(pc),d2
        divu.w #10,d2
.wait:
        move.l MODAL_FIELD(a4),d0
        sub.l modal_room_cursor(pc),d0
        cmp.l d2,d0
        bcc.s .due
        bsr.w modal_room_poll
        bsr.w modal_bar_between
        bra.s .wait
.due:
        ; Room entry/dialogs deliberately rebase. Ordinary rendering overload
        ; keeps the cursor behind so no native animation step is invented.
        lea modal_room_cursor(pc),a0
        add.l d2,(a0)
        movem.l (sp)+,d0-d2/a0
        rts

; Poll cursor/hotspots at 25 Hz (two PAL fields, alternating NTSC intervals).
; Keep the first selected action until the owning room loop consumes it. Further
; polling must not replace a short click or enter a dialog from this wait stack.
modal_room_poll:
        movem.l d0-d7/a0-a6,-(sp)
        tst.w modal_room_result(pc)
        bpl.s .done
        move.l MODAL_FIELD(a4),d0
        lea modal_room_input_field(pc),a0
        move.l d0,d1
        sub.l (a0),d0
        move.l d1,(a0)
        lea modal_room_input_phase(pc),a0
        cmpi.l #3,d0
        bhi.s .late
        mulu.w #25,d0
        moveq #0,d1
        move.w (a0),d1
        add.l d1,d0
        cmp.w modal_hz(pc),d0
        blo.s .not_due
        divu.w modal_hz(pc),d0
        swap d0
        move.w d0,(a0)
        bra.s .poll
.not_due:
        move.w d0,(a0)
        bra.s .done
.late:
        clr.w (a0)             ; one sample after a stall, no cursor catch-up
.poll:
        lea modal_label_previous(pc),a0
        clr.l (a0)
        lea modal_room_polling(pc),a0
        move.w #1,(a0)
        move.l modal_room_table(pc),-(sp)
        bsr.w modal_room_native_input
        addq.l #4,sp
        lea modal_room_polling(pc),a0
        clr.w (a0)
        lea modal_room_result(pc),a0
        move.w d0,(a0)
.done:
        movem.l (sp)+,d0-d7/a0-a6
        rts
modal_room_input:
        bsr.w modal_room_poll
        bsr.w modal_label_replay
        move.w modal_room_result(pc),d0
        move.l a0,-(sp)
        lea modal_room_result(pc),a0
        move.w #-1,(a0)
        move.l (sp)+,a0
        rts
modal_room_table: dc.l 0
modal_room_input_field: dc.l -1
modal_room_result: dc.w -1
modal_room_input_phase: dc.w 0
modal_room_polling: dc.w 0
        even

; D0=shot duration, A3=native end field. Sample positions continuously,
; frames discretely at 10 Hz. The original shot's field deadline is retained.
modal_run_sample:
        movem.l d0-d2/a0,-(sp)
        move.l a3,d1
        sub.l d0,d1
        move.l MODAL_FIELD(a4),d0
        sub.l d1,d0
        cmpi.l #600,d0
        bls.s .bounded
        move.l #600,d0
.bounded:
        move.l d0,d2
        ; The shared prediction payload can put the clock beyond d16(PC).
        lea modal_run_sample(pc),a0
        adda.l #MODAL_HZ-modal_run_sample,a0
        move.l (a0),d0
        lea modal_hz(pc),a0
        move.w d0,(a0)
        move.l d2,d0
        mulu.w #10,d0
        move.l d0,d1
        divu.w modal_hz(pc),d0
        andi.l #$ffff,d0
        lea modal_run_tick(pc),a0
        move.w d0,(a0)
        move.l d1,d0
        mulu.w #12,d0
        divu.w modal_hz(pc),d0
        neg.w d0
        andi.w #$fffe,d0       ; native OCS checkerboard background phase
        lea modal_run_x(pc),a0
        move.w d0,(a0)
        move.l d1,d0
        add.l d0,d0
        divu.w modal_hz(pc),d0
        move.w d0,d5
        move.l d1,d0
        mulu.w #3,d0
        divu.w modal_hz(pc),d0
        move.w d0,d6
        move.w #1,MODAL_COUNTDOWN(a4)
        movem.l (sp)+,d0-d2/a0
        rts
modal_run_upper:
        moveq #0,d0
        move.w 36(sp),d0
        bsr.w modal_run_sample
        addi.w #70,d5
        addi.w #170,d6
        move.w modal_run_x(pc),d7
        moveq #0,d0
        move.w modal_run_tick(pc),d0
        divu.w #13,d0
        swap d0
        move.w d0,d3
        addq.w #7,d3
        moveq #0,d0
        move.w modal_run_tick(pc),d0
        addq.w #3,d0
        divu.w #13,d0
        swap d0
        move.w d0,d4
        addq.w #7,d4
        bra.w modal_upper_resume
modal_run_feet:
        moveq #0,d0
        move.w 36(sp),d0
        bsr.w modal_run_sample
        addi.w #90,d5
        addi.w #200,d6
        move.w modal_run_x(pc),d2
        moveq #0,d0
        move.w modal_run_tick(pc),d0
        divu.w #6,d0
        swap d0
        move.w d0,d3
        addi.w #21,d3
        moveq #0,d0
        move.w modal_run_tick(pc),d0
        addq.w #3,d0
        divu.w #6,d0
        swap d0
        move.w d0,d4
        addi.w #21,d4
        bra.w modal_feet_resume

; Ready/Game Over share the native text fly-in, but not flight input/scoring.
; C ABI: text.l, delay.w, initial-depth.w, unused.w, particle-flag.w.
; Only the two known zero-particle callers are redirected here.
modal_simulator:
        link a5,#-4
        movem.l d2-d7/a2-a6,-(sp)
        movea.l MODAL_CONTEXT(a4),a2
        move.l a2,d0
        bne.s .context
        bsr.w modal_context_begin
.context:
        clr.w MODAL_ABORT(a4)
        bsr.w intro_start
        clr.w -2(a5)
.loop:
        bsr.w intro_due
        move.w d0,d2
.ticks:
        tst.w d2
        beq.s .draw
        bsr.w intro_world
        addq.w #1,-2(a5)
        cmpi.w #40,-2(a5)
        bhs.w .done
        subq.w #1,d2
        bra.s .ticks
.draw:
        bsr.w intro_draw
        move.w -2(a5),d0
        cmp.w 12(a5),d0
        ble.s .finish
        ; Smooth depth on the same tick/fraction clock as the world. Render
        ; prediction is restored by intro_finish, never committed to objects.
        moveq #0,d0
        move.w -2(a5),d0
        mulu.w #10,d0
        move.l d0,d3
        move.l a0,-(sp)
        lea modal_run_sample(pc),a0
        adda.l #MODAL_CLOCK+4-modal_run_sample,a0
        move.l (a0),d0
        mulu.w #10,d0
        adda.l #MODAL_HZ+2-(MODAL_CLOCK+4),a0
        divu.w (a0),d0
        move.l (sp)+,a0
        andi.l #$ffff,d0
        add.l d0,d3
        moveq #0,d1
        move.w 14(a5),d1
        sub.l d3,d1
        cmpi.l #100,d1
        bge.s .depth
        moveq #100,d1
.depth:
        move.l #51200,d0
        bsr.w modal_divide
        move.w d0,-(sp)
        move.w MODAL_CENTRE_Y(a4),-(sp)
        move.w MODAL_CENTRE_X(a4),-(sp)
        move.l 8(a5),-(sp)
        bsr.w modal_text
        lea 10(sp),sp
.finish:
        bsr.w intro_finish
        bsr.w modal_input
        tst.w d0
        bne.s .done
        tst.w MODAL_ABORT(a4)
        bne.s .done
        cmpi.w #40,-2(a5)
        blo.w .loop
.done:
        bsr.w intro_stop
        clr.w MODAL_ABORT(a4)
        move.l a2,d0
        bne.s .restore
        bsr.w modal_context_end
.restore:
        movem.l (sp)+,d2-d7/a2-a6
        unlk a5
        rts
modal_hz: dc.w 50
modal_run_tick: dc.w 0
modal_run_x: dc.w 0
        even
modal_room_cursor: dc.l 0

; Snapshot the positions actually drawn by the authoritative window pass.
; Intermediate fields draw these records plus fractional velocity, without
; executing native respawn/RNG/frame changes or writing game records.
modal_bar_capture:
        movem.l d0-d1/a0-a1,-(sp)
        lea modal_bar_count(pc),a1
        move.w BAR_MOVING_COUNT(a4),d0
        cmpi.w #64,d0
        bhi.s .invalid
        move.w d0,(a1)
        lea BAR_MOVING(a4),a0
        lea modal_bar_records(pc),a1
        add.w d0,d0
        beq.s .ready
        subq.w #1,d0
.copy:  move.l (a0)+,(a1)+
        dbra d0,.copy
.ready:
        lea modal_bar_epoch(pc),a0
        move.l MODAL_FIELD(a4),(a0)
        lea modal_bar_last(pc),a0
        move.l MODAL_FIELD(a4),(a0)
        bra.s .done
.invalid:
        move.w #-1,(a1)
.done:
        movem.l (sp)+,d0-d1/a0-a1
        rts
modal_bar_between:
        movem.l d0-d7/a0-a6,-(sp)
        tst.w modal_bar_enabled(pc)
        beq.w .done
        tst.w modal_bar_count(pc)
        bmi.w .done
        move.l MODAL_FIELD(a4),d7
        cmp.l modal_bar_last(pc),d7
        beq.w .done
        lea modal_bar_last(pc),a0
        move.l d7,(a0)
        sub.l modal_bar_epoch(pc),d7
        mulu.w #10,d7
        cmp.w modal_hz(pc),d7
        bhs.w .done
        movea.l BAR_SURFACE(a4),a3
        move.b BAR_COLOUR(a4),-(sp)
        move.l a3,-(sp)
        bsr.w modal_bar_clear
        addq.l #6,sp
        lea BAR_STATIC(a4),a2
        move.w BAR_STATIC_COUNT(a4),d2
        bra.s .static_test
.static:
        move.w 4(a2),-(sp)
        move.l BAR_IMAGE(a4),-(sp)
        move.w 2(a2),-(sp)
        move.w (a2),-(sp)
        move.l a3,-(sp)
        bsr.w modal_bar_bitmap
        lea 14(sp),sp
        addq.l #6,a2
.static_test:
        dbra d2,.static_body
        bra.s .moving_start
.static_body:
        bra.s .static
.moving_start:
        lea modal_bar_records(pc),a2
        move.w modal_bar_count(pc),d2
        bra.s .moving_test
.moving:
        move.w 4(a2),d0
        muls.w d7,d0
        divs.w modal_hz(pc),d0
        add.w (a2),d0
        move.w 6(a2),-(sp)
        move.l BAR_IMAGE(a4),-(sp)
        move.w 2(a2),-(sp)
        move.w d0,-(sp)
        move.l a3,-(sp)
        bsr.w modal_bar_bitmap
        lea 14(sp),sp
        addq.l #8,a2
.moving_test:
        dbra d2,.moving_body
        bsr.w modal_bar_restore
        bsr.w modal_portrait_replay
        bsr.w modal_label_replay
        bsr.w modal_bar_publish
        bra.s .done
.moving_body:
        bra.s .moving
.done:
        movem.l (sp)+,d0-d7/a0-a6
        rts
modal_bar_enabled: dc.w 0
modal_bar_count: dc.w -1
modal_bar_epoch: dc.l 0
modal_bar_last: dc.l 0
modal_bar_records: ds.b 512

; The window overlaps the bartender. Repaint the exact last native foreground
; pose after every intermediate window image. Native script pointers, RNG and
; animation counter are restored, so this presentation cannot advance a script.
modal_portraits:
        movem.l d0/a0-a1,-(sp)
        lea BAR_POINTERS(a4),a0
        lea modal_portrait_state(pc),a1
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        move.l BAR_RNG(a4),(a1)+
        move.w BAR_DRAW_COUNT(a4),(a1)+
        move.l 16(sp),(a1)
        movem.l (sp)+,d0/a0-a1
        bra.w modal_portrait_native
modal_portrait_replay:
        movem.l d0-d7/a0-a6,-(sp)
        move.l BAR_POINTERS(a4),-(sp)
        move.l BAR_POINTERS+4(a4),-(sp)
        move.l BAR_POINTERS+8(a4),-(sp)
        move.l BAR_RNG(a4),-(sp)
        move.w BAR_DRAW_COUNT(a4),-(sp)
        lea modal_portrait_state(pc),a0
        lea BAR_POINTERS(a4),a1
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        move.l (a0)+,BAR_RNG(a4)
        move.w (a0)+,BAR_DRAW_COUNT(a4)
        move.l (a0),-(sp)
        bsr.w modal_portrait_native
        addq.l #4,sp
        move.w (sp)+,BAR_DRAW_COUNT(a4)
        move.l (sp)+,BAR_RNG(a4)
        move.l (sp)+,BAR_POINTERS+8(a4)
        move.l (sp)+,BAR_POINTERS+4(a4)
        move.l (sp)+,BAR_POINTERS(a4)
        movem.l (sp)+,d0-d7/a0-a6
        rts
modal_portrait_state: ds.b 22

; Input selects a title; composition owns its pixels. Room redraws overwrite
; the strip even when the pointer has not moved. Never manufacture a clear:
; native transparent labels deliberately skip the colour-fill call.
modal_label_begin:
        tst.w modal_room_polling(pc)
        beq.w modal_label_native_clear
        rts
modal_label_print:
        tst.w modal_room_polling(pc)
        beq.w modal_label_native_print
        move.l a0,-(sp)
        lea modal_label_format(pc),a0
        move.l 8(sp),(a0)+
        move.l 12(sp),(a0)
        move.l (sp)+,a0
        rts
modal_label_end:
        bra.w modal_label_native_cursor

; Called after native room composition and after intermediate bar restoration.
; Recreate the native text context/reset and honour its transparent sentinel.
modal_label_replay:
        movem.l d0-d7/a0-a6,-(sp)
        move.l MODAL_LABEL_SURFACE(a4),d0
        beq.s .done
        move.b MODAL_LABEL_COLOUR(a4),d0
        cmp.b MODAL_TRANSPARENT(a4),d0
        beq.s .text
        move.b d0,-(sp)
        move.l MODAL_LABEL_SURFACE(a4),-(sp)
        bsr.w modal_label_native_clear
        addq.l #6,sp
.text:
        tst.l modal_label_previous(pc)
        beq.s .done
        move.l MODAL_TEXT_CONTEXT(a4),-(sp)
        lea MODAL_LABEL_CONTEXT(a4),a0
        move.l a0,MODAL_TEXT_CONTEXT(a4)
        bsr.w modal_label_native_reset
        move.l modal_label_previous(pc),-(sp)
        move.l modal_label_format(pc),-(sp)
        bsr.w modal_label_native_print
        addq.l #8,sp
        move.l (sp)+,MODAL_TEXT_CONTEXT(a4)
.done:
        movem.l (sp)+,d0-d7/a0-a6
        rts
modal_label_format: dc.l 0
modal_label_previous: dc.l 0
