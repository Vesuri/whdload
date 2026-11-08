; VERIFY-only coupling experiment. Both runs install identical instrumentation;
; CUSTOM5 bit 8 adds eight PAL fields before each renderer entry after the anchor.
; No simulation timing is changed. Never included in normal or performance builds.
_timing_study_install
        movem.l d0-a6,-(sp)
        move.l (_h12,pc),a0
        cmp.l #$48e73f3e,(h12_027bc,a0)
        bne .bad
        cmp.l #$6100fc14,(h12_027c0,a0)
        bne .bad
        cmp.l #$303900df,(h12_0643e,a0)
        bne .bad
        cmp.w #$f00a,(h12_06442,a0)
        bne .bad
        lea (h12_06444,a0),a1
        lea (_timing_study_mouse_continue,pc),a2
        move.l a1,(a2)
        move.w #$4ef9,(h12_0643e,a0)
        lea (_timing_study_mouse,pc),a1
        move.l a1,(h12_06440,a0)
        move.w #$4ef9,(h12_027bc,a0)
        lea (_timing_study_render,pc),a1
        move.l a1,(h12_027be,a0)
        move.w #$4e71,(h12_027c2,a0)
        bsr _timing_combat_install
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        bsr _timing_keys_install
        movem.l (sp)+,d0-a6
        rts
.bad    lea (_timing_study_bad,pc),a0
        bra _c2p_abort
_timing_study_render
        movem.l d0-a6,-(sp)
_verify_sr_17 EQU *
        move.w sr,-(sp)
        move.w (_timing_study_armed,pc),d0
        beq .restore
        ; Delay only actual output ticks when the simulation scheduler is active.
        move.l (_custom2,pc),d0
        btst #6,d0
        beq .option
        move.w (_sim_render_tick,pc),d0
        beq .restore
.option
        move.l (_custom5,pc),d0
        btst #8,d0
        bne .delay
        move.w (_timing_study_tape_delay,pc),d0
        beq .restore
.delay
        move.l (_h11,pc),a0
        move.w (h11_0602e,a0),d1
.wait   move.w (h11_0602e,a0),d0
        sub.w d1,d0
        cmp.w #8,d0
        bcs .wait
        lea (_timing_study_delays,pc),a0
        addq.l #1,(a0)
.restore
        move.w (sp)+,ccr
        movem.l (sp)+,d0-a6
        movem.l d2-d7/a2-a6,-(sp)
        pea .prepared(pc)
        move.l (_h12,pc),-(sp)
        add.l #h12_023d6,(sp)
        rts
.prepared
        move.l (_h12,pc),-(sp)
        add.l #h12_027c4,(sp)
        rts
_timing_study_bad dc.b "TIMING study: unexpected renderer entry",0
        EVEN
_timing_study_tape_delay dc.w 0
_timing_study_armed dc.w 0
_timing_study_delays dc.l 0

; A requested tape anchor can land inside a newly timed greeting. Defer the
; study window until the original pause gate opens; use only ordinary input
; to leave the dialog. The two comparison runs remain identical until ready.
_timing_study_wait_ready
        move.w (_timing_study_pending,pc),d0
        beq .done
        move.l (_h12,pc),a0
        adda.l #h12_0a0c3,a0
        tst.b (a0)
        bne .ready
        move.l (_h11,pc),a0
        move.l (h11_05eb0,a0),d0
        beq .done
        move.l d0,a0
        move.w #75,($e,a0)
        move.w #183,($c,a0)
        move.l (_tapefield,pc),d0
        and.w #63,d0
        cmp.w #48,d0
        scs d0
        not.b d0
        and.w #1,d0
        move.l (_h12,pc),a0
        move.w d0,(h12_05292,a0)
.done   rts
.ready  lea (_timing_study_pending,pc),a0
        clr.w (a0)
        lea (_timing_study_armed,pc),a0
        move.w #1,(a0)
        ; VERIFY-only deliberate time jump: cross a day boundary 16 fields later.
        ; Both controls use identical CUSTOM5 options; A/D selects drawing delay.
        move.l (_custom5,pc),d0
        btst #12,d0
        beq _timing_study_ready
        move.l (_h11,pc),a0
        move.w #$fff0,(h11_004d8,a0)
_timing_study_ready
        nop
        rts
_timing_study_pending dc.w 0


; CUSTOM5 bit 9: a field-timed turn-button pulse after the active anchor.
; Both comparison runs receive a four-field press after eight idle fields. This
; intentionally exposes render-dependent input consumption in candidate patches.
_timing_study_input
        move.w (_timing_study_armed,pc),d0
        beq .done
        lea (_timing_study_watch_fields,pc),a0
        addq.l #1,(a0)
        bsr _timing_keys_wake
        move.l (_custom5,pc),d0
        IFD TIMING_KEYS_TEXT
        bra .long_watch
        ENDC
        btst #28,d0
        bne .long_watch
        btst #20,d0
        beq .ordinary_watch
.long_watch
        cmp.l #2048,(a0)
        bcs .input
        bra .expired
.ordinary_watch
        and.l #$12000,d0
        beq .short_watch
        cmp.l #1024,(a0)
        bcs .input
        bra .expired
.short_watch
        cmp.l #512,(a0)
        bcs .input
.expired
        bsr _timing_study_watchdog
.input
        move.w (_timing_study_panel_active,pc),d0
        beq .ordinary
        bsr _timing_study_panel_input
        rts
.ordinary
        move.l (_custom5,pc),d0
        btst #29,d0
        beq .ordinary_options
        bsr _timing_combat_input
        rts
.ordinary_options
        btst #12,d0
        beq .pulse_option
        ; The deliberate clock jump can display a click-to-dismiss message.
        ; Use native input only while the original game pause gate is closed.
        move.l (_h12,pc),a0
        adda.l #h12_0a0c3,a0
        tst.b (a0)
        beq .modal
.pulse_option
        btst #9,d0
        beq .done
        move.l (_h11,pc),a0
        move.l (h11_05eb0,a0),d0
        beq .done
        move.l d0,a0
        move.w #143,($e,a0)
        move.w #148,($c,a0)
        lea (_timing_study_input_fields,pc),a0
        move.l (a0),d0
        addq.l #1,(a0)
        subq.l #8,d0
        move.l (_custom5,pc),d1
        btst #23,d1
        beq .short_press
        cmp.l #40,d0
        bra .press_condition
.short_press
        cmp.l #4,d0
.press_condition
        scs d0
        and.w #1,d0
        move.l (_custom5,pc),d1
        btst #11,d1
        beq .buttons
        moveq #0,d0
.buttons
        move.l (_h12,pc),a0
        move.w d0,(h12_05292,a0)
.done   rts
.modal  move.l (_h11,pc),a0
        move.l (h11_05eb0,a0),d0
        beq .done
        move.l d0,a0
        move.w #75,($e,a0)
        move.w #183,($c,a0)
        move.l (_timing_study_watch_fields,pc),d0
        and.w #31,d0
        subq.w #8,d0
        cmp.w #4,d0
        scs d0
        and.w #1,d0
        move.l (_h12,pc),a0
        move.w d0,(h12_05292,a0)
        rts
        CNOP 0,4
_timing_study_input_fields dc.l 0
_timing_study_watch_fields dc.l 0
; Read-only debugger escape if a tick observer encounters a blocking modal.
; Outside observation this returns immediately and does not alter gameplay.
_timing_study_watchdog
        rts


; CUSTOM5 bit 11: substitute four +5-count hardware X increments in the same
; input window. Bit 14 instead selects 48 negative five-count increments,
; crossing the hardware-counter and heading zero boundaries.
; The original game's JOYDAT delta calculation consumes these,
; so the VERIFY legacy control and the buffered path receive identical motion.
_timing_study_mouse
        move.l d1,-(sp)
        ; A scripted study owns relative input as well as buttons/pointer.
        ; JOY0=none has still produced external counter changes in a capture.
        ; Hold both counters at zero unless this fixture injects X below.
        ; Preserve D0's upper word, matching the original MOVE.W read.
        move.w #0,d0
        move.l (_custom5,pc),d1
        btst #11,d1
        beq .done
        move.w (_timing_study_armed,pc),d1
        beq .apply
        IFD TIMING_MODE_TEST
        move.l (_timing_study_watch_fields,pc),d1
        ELSE
        move.l (_timing_study_input_fields,pc),d1
        ENDC
        subq.l #8,d1
        move.l d0,-(sp)
        move.l (_custom5,pc),d0
        IFD TIMING_MODE_TEST
        ; Repeated native mode toggles come from the ordinary tape. Supply
        ; negative hardware-counter deltas in both modes, including transitions.
        cmp.l #192,d1
        bcc .restore
        move.l a0,-(sp)
        lea (_timing_study_mouse_x,pc),a0
        subq.b #5,(a0)
        move.l (sp)+,a0
        bra .restore
        ENDC
        btst #20,d0
        bne .fine
        btst #14,d0
        bne .negative
        cmp.l #4,d1
        bcc .restore
        move.l a0,-(sp)
        lea (_timing_study_mouse_x,pc),a0
        addq.b #5,(a0)
        move.l (sp)+,a0
        bra .restore
.fine
        ; One hardware count every two PAL fields: a complete 360-degree
        ; sweep at one degree per 25 Hz tick. Bit 14 chooses reverse.
        cmp.l #720,d1
        bcc .restore
        btst #0,d1
        bne .restore
        move.l a0,-(sp)
        lea (_timing_study_mouse_x,pc),a0
        btst #14,d0
        bne .fine_reverse
        addq.b #1,(a0)
        bra .fine_done
.fine_reverse
        subq.b #1,(a0)
.fine_done
        move.l (sp)+,a0
        bra .restore
.negative
        cmp.l #48,d1
        bcc .restore
        move.l a0,-(sp)
        lea (_timing_study_mouse_x,pc),a0
        subq.b #5,(a0)
        move.l (sp)+,a0
.restore
        move.l (sp)+,d0
.apply  add.b (_timing_study_mouse_x,pc),d0
.done   move.l (sp)+,d1
        move.l (_timing_study_mouse_continue,pc),-(sp)
        rts
_timing_study_mouse_x dc.w 0
        CNOP 0,4
_timing_study_mouse_continue dc.l 0

        INCLUDE "timing_panel.s"

; Bit 16: deliberately exceed the history capacity in the main task once.
; VBL and input sampling continue normally; the shipping build excludes this.
_timing_study_stall
        movem.l d0-d1/a0,-(sp)
        move.l (_custom5,pc),d0
        btst #16,d0
        beq .done
        move.w (_timing_study_armed,pc),d0
        beq .done
        lea (_timing_study_stalled,pc),a0
        tst.w (a0)
        bne .done
        move.w #1,(a0)
        move.l (_h11,pc),a0
        move.l (h11_0602c,a0),d1
.wait   move.l (h11_0602c,a0),d0
        sub.l d1,d0
        cmp.l #600,d0
        bcs .wait
.done   movem.l (sp)+,d0-d1/a0
        rts
_timing_study_stalled dc.w 0

        INCLUDE "timing_keys.s"

        INCLUDE "timing_combat.s"

        IFD TIMING_PROJECTILE
        INCLUDE "timing_projectile.s"
        ENDC
