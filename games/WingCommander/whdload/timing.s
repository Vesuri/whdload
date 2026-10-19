; Experimental English CUSTOM1=3 simulation and renderer-prediction adapter.
; Flight delta conversion is separate from the intro renderer/release options.
; Original language choices CUSTOM1=0/1 install no new game patches.

; Diagnostic frame-part record (--frame-stats); expands to nothing otherwise.
FSTAT   macro
        ifne FRAME_STATS
        move.w  #\1,-(sp)
        bsr.w   frame_stat
        addq.l  #2,sp
        endif
        endm
timing_converter_entry:
        bra.l   flight_render_entry

timing_patchseg:
        jsr     116(a2)
        movem.l d0-d7/a0-a6,-(sp)
        move.w  ccr,-(sp)
        move.l  slave+$1de4(pc),d0
        cmpi.l  #3,d0
        bne.w   .done
        move.l  d7,d0
        lsl.l   #2,d0
        addq.l  #4,d0
        movea.l d0,a0
        lea     timing_game(pc),a1
        move.l  a0,(a1)
        ; The builder generates exact pinned-input guards and patches in tmp.
        bsr.w   timing_install
        bsr.w   timing_rate
        lea     timing_hz(pc),a0
        move.l  d0,(a0)
        bsr.l   flight_render_init
        jsr     32(a2)
.done:
        move.w  (sp)+,ccr
        movem.l (sp)+,d0-d7/a0-a6
        rts

timing_bad:
        move.l  slave+$121e(pc),a2
        pea     9
        jmp     4(a2)

; Same beam-line classification as Their Finest Hour. The observation covers
; a whole field, including two agreeing reads across the line-255 boundary.
timing_rate:
        movem.l d1-d3,-(sp)
        bsr.s   .line
.sync:
        move.w  d0,d1
        bsr.s   .line
        cmp.w   d1,d0
        bhs.s   .sync
        moveq   #0,d2
.field:
        cmp.w   d2,d0
        bls.s   .next
        move.w  d0,d2
.next:
        move.w  d0,d1
        bsr.s   .line
        cmp.w   d1,d0
        bhs.s   .field
        moveq   #50,d0
        cmpi.w  #288,d2
        bhs.s   .done
        moveq   #60,d0
.done:
        movem.l (sp)+,d1-d3
        rts
.line:
        move.l  $dff004,d0
        lsr.l   #8,d0
        andi.w  #$1ff,d0
        move.l  $dff004,d3
        lsr.l   #8,d3
        andi.w  #$1ff,d3
        cmp.w   d0,d3
        bne.s   .line
        rts

; Ordinary loop consumes timestamped native input in chronological field order.
; It services at most four ticks per batch and skips drawing while catching up.
timing_loop:
        movem.l d0-d7/a0-a6,-(sp)
        ; Load initial flight assets on the original input/world path, before
        ; enabling the producer. This initial update establishes the epoch.
        bsr.w   timing_native_input
        tst.w   -32628(a4)
        bne.w   timing_leave
        bsr.w   timing_world
        bsr.w   timing_rebase
        lea     timing_active(pc),a0
        move.w  #1,(a0)
.loop:
        FSTAT   1
        ifne FRAME_STATS
        bsr.w   frame_stats_flush
        endif
        tst.w   -32628(a4)
        bne.w   timing_leave
        tst.w   timing_input_lost(pc)
        beq.s   .budget
        lea     timing_input_recoveries(pc),a0
        addq.l  #1,(a0)
        bsr.w   timing_rebase
.budget:
        move.l  timing_hz(pc),d7
        divu.w  #10,d7
        andi.l  #$ffff,d7
        lsl.w   #2,d7
.fields:
        bsr.w   timing_take_sample
        tst.w   d0
        beq.w   .draw
        lea     timing_replay(pc),a0
        move.w  #1,(a0)
        ; Merge the frozen keyboard and pad sample through the native decoder.
        pea     timing_sample_pad(pc)
        move.l  timing_game(pc),a6
        jsr     $18c5e(a6)
        addq.l  #4,sp
        bsr.w   timing_preview_controls
        bsr.w   timing_player_field
        bsr.w   timing_queue_pad
        move.l  timing_sample_clock(pc),d0
        move.l  timing_hz(pc),d1
        moveq   #1,d2
        lea     timing_clock(pc),a0
        bsr.w   timing_advance
        move.l  d0,d6
        tst.l   d6
        beq.s   .next_field
        bsr.w   timing_edge_geometry
        bsr.w   timing_pad_edges
        tst.w   -32628(a4)
        bne.w   timing_leave
        tst.w   timing_abort(pc)
        bne.s   .cancel
        bsr.w   timing_target_tick
        bsr.w   timing_native_input
        tst.w   -32628(a4)
        bne.w   timing_leave
        tst.w   timing_abort(pc)
        bne.s   .cancel
        lea     timing_in_world(pc),a0
        move.w  #1,(a0)
        bsr.w   timing_world
        lea     timing_in_world(pc),a0
        clr.w   (a0)
.next_field:
        tst.w   -32628(a4)
        bne.w   timing_leave
        subq.w  #1,d7
        bne.w   .fields
        ; More captured fields mean debt, so run another bounded batch first.
        move.w  timing_input_tail(pc),d0
        cmp.w   timing_input_head(pc),d0
        bne.w   .loop
        bra.s   .draw
.cancel:
        lea     timing_clock(pc),a0
        sub.l   d6,12(a0)
        move.l  d6,d0
        mulu.w  timing_hz+2(pc),d0
        add.l   d0,16(a0)
        lea     timing_abort(pc),a0
        clr.w   (a0)
.draw:
        FSTAT   4
        lea     timing_selection_last(pc),a0
        move.w  4430(a4),d0
        move.w  d0,d1
        sub.w   (a0),d0
        move.w  d1,(a0)
        lea     timing_selection_delta(pc),a0
        move.w  d0,(a0)
        bsr.w   timing_player_camera
        bsr.w   timing_render
        bra.w   .loop

timing_render:
        ifne TIMING_VERIFY
        move.l  -252(a4),-(sp)
        cmpi.w  #1,timing_verify_schedule(pc)
        beq.s   .wait
        endc
        bsr.w   timing_scene_begin
        FSTAT   5
        move.l  -4326(a4),-(sp)
        move.l  timing_render_seed(pc),-4326(a4)
        move.l  timing_game(pc),a6
        jsr     $510(a6)
        FSTAT   6
        move.l  timing_game(pc),a6
        jsr     $46e6(a6)
        FSTAT   7
        lea     timing_render_seed(pc),a0
        move.l  -4326(a4),(a0)
        move.l  (sp)+,-4326(a4)
        bsr.w   timing_scene_end
        FSTAT   8
        ifne TIMING_VERIFY
.wait:
        moveq   #0,d0
        move.w  timing_verify_schedule(pc),d0
        beq.s   .finish
.again:
        move.l  -252(a4),d1
        sub.l   (sp),d1
        cmp.l   d0,d1
        blo.s   .again
.finish:
        addq.l  #4,sp
        endc
        rts

timing_native_input:
        move.l  timing_game(pc),a6
        jsr     $19330(a6)
        cmpi.w  #-1,d0
        bne.s   .done
        move.w  #5,-32628(a4)
.done:
        rts

timing_world:
        ifne BUFFERED
        ifne FRAME_STATS
        bsr.w   translation_tick_begin
        endif
        endif
        FSTAT   2
        move.l  timing_game(pc),a6
        jsr     $2a8(a6)
        ifne BUFFERED
        ifne FRAME_STATS
        bsr.w   translation_tick_end
        endif
        endif
        tst.w   timing_active(pc)
        beq.s   timing_world_done
        bsr.w   timing_presentation_tick
        bsr.w   timing_scene_tick
timing_world_done:
        FSTAT   3
        lea     timing_completed(pc),a0
        addq.l  #1,(a0)
        lea     timing_abort(pc),a0
        clr.w   (a0)
        rts

timing_rebase:
        movem.l d0-d3/a0,-(sp)
        ; Producer sees inactive before unread history is discarded. Single
        ; word stores publish ownership; no interrupt masking or device writes.
        lea     timing_active(pc),a0
        move.w  (a0),-(sp)
        clr.w   (a0)
        tst.w   (sp)
        beq.s   .discarded
        move.l  -252(a4),d0
        sub.l   timing_clock(pc),d0
        lea     timing_input_dropped_fields(pc),a0
        add.l   d0,(a0)
        mulu.l  #10,d0
        lea     timing_clock+16(pc),a0
        add.l   d0,(a0)
.discarded:
        bsr.w   timing_prediction_reset
        lea     timing_input_tail(pc),a0
        move.w  timing_input_head(pc),(a0)
        lea     timing_input_lost(pc),a0
        clr.w   (a0)
        lea     timing_replay(pc),a0
        clr.w   (a0)
        lea     timing_pad_count(pc),a0
        clr.l   (a0)
        lea     timing_selection_last(pc),a0
        move.w  4430(a4),(a0)
        clr.w   2(a0)
        lea     timing_angle_remainder(pc),a0
        clr.l   (a0)+
        clr.l   (a0)+
        clr.l   (a0)
        move.l  -252(a4),d0
        move.l  timing_hz(pc),d1
        moveq   #0,d2
        lea     timing_clock(pc),a0
        bsr.w   timing_advance
        move.l  -252(a4),d0
        move.l  timing_hz(pc),d1
        moveq   #1,d2
        bsr.w   timing_advance
        lea     timing_active(pc),a0
        move.w  (sp)+,(a0)
        movem.l (sp)+,d0-d3/a0
        rts

timing_leave:
        tst.w   timing_active(pc)
        beq.s   .rebasing
        bsr.w   timing_scene_geometry
.rebasing:
        bsr.w   timing_rebase
        lea     timing_active(pc),a0
        clr.w   (a0)
        movem.l (sp)+,d0-d7/a0-a6
        move.l  timing_exit(pc),-(sp)
        rts

timing_pause:
        move.l  a6,-(sp)
        move.l  a0,-(sp)
        lea     timing_active(pc),a0
        move.w  (a0),-(sp)
        bsr.w   timing_rebase
        clr.w   (a0)
        lea     timing_replay(pc),a0
        clr.w   (a0)
        bsr.l   timing_pause_original
        move.w  ccr,-(sp)
        bsr.w   timing_rebase
        lea     timing_abort(pc),a0
        move.w  #1,(a0)
        lea     timing_active(pc),a0
        move.w  2(sp),(a0)
        move.w  (sp)+,ccr
        lea     2(sp),sp
        move.l  (sp)+,a0
        move.l  (sp)+,a6
        rts

timing_autopilot:
        move.l  a6,-(sp)
        move.l  a0,-(sp)
        lea     timing_active(pc),a0
        move.w  (a0),-(sp)
        bsr.w   timing_rebase
        clr.w   (a0)
        lea     timing_replay(pc),a0
        clr.w   (a0)
        bsr.w   timing_autopilot_original
        move.w  ccr,-(sp)
        bsr.w   timing_rebase
        lea     timing_abort(pc),a0
        move.w  #1,(a0)
        lea     timing_active(pc),a0
        move.w  2(sp),(a0)
        move.w  (sp)+,ccr
        lea     2(sp),sp
        move.l  (sp)+,a0
        move.l  (sp)+,a6
        rts

        cnop    0,4
timing_game:      dc.l 0
timing_exit:      dc.l 0
timing_hz:        dc.l 0
timing_active:    dc.w 0
timing_abort:     dc.w 0
timing_clock:    dcb.b 28,0
timing_completed: dc.l 0

        ifne TIMING_VERIFY
timing_verify_schedule: dc.w 0
        endc
