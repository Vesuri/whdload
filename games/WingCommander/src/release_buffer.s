; Predict from the last consumed world-clock sample to the earliest display
; field: one blank after this picture is queued, plus an outstanding swap.
; The IRQ may retire the pending picture while this snapshot is taken.
release_predict:
.sample:
        move.l  A_m252(a4),d0
        moveq   #0,d1
        move.w  release_pending(pc),d1
        cmp.l   A_m252(a4),d0
        bne.s   .sample
        addq.l  #1,d0
        add.l   d1,d0
        lea     release_render_time(pc),a0
        move.l  d0,(a0)+         ; target display field
        move.l  timing_clock(pc),(a0)+
        move.l  timing_clock+4(pc),(a0)+
        sub.l   timing_clock(pc),d0
        mulu.l  #10,d0
        add.l   timing_clock+4(pc),d0
        move.l  d0,d6
        move.l  timing_hz(pc),d7
        move.l  d7,d0
        addi.l  #20,d0           ; one tick plus at most two queued fields
        cmp.l   d0,d6
        bls.s   .bounded
        move.l  d0,d6            ; a longer stall is not unbounded extrapolation
.bounded:
        move.l  d6,(a0)
        rts

; Enhanced flight/world intro: queue after conversion; retire the front in VBL.
; Main thread owns request data until pending=1; IRQ owns it until pending=0.
; No allocation, OS calls, or third buffer. Other scenes retain native publication.
release_publish:
        tst.w   timing_active(pc)
        bne.s   .enhanced
        tst.w   intro_active(pc)
        beq.w   .native
.enhanced:
        bsr.w   release_buffer_wait
        movem.l d0/a0-a1,-(sp)
        move.l  timing_game(pc),a0
        move.w  E_33210(a0),d0     ; completed index, after E:33772
        lea     release_pending_index(pc),a1
        move.w  d0,(a1)
        lea     release_pending_a4(pc),a1
        move.l  a4,(a1)
        andi.l  #1,d0
        lsl.w   #2,d0
        lea     E_331f8(a0),a0
        move.l  (a0,d0.w),d0
        lea     release_pending_plane(pc),a1
        move.l  d0,(a1)
        lea     release_render_time(pc),a0
        lea     release_pending_time(pc),a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        FSTAT   16
        lea     release_pending(pc),a0
        move.w  #1,(a0)          ; publish request last
        movem.l (sp)+,d0/a0-a1
        rts
.native:
        bsr.w   release_buffer_wait
        lea     release_front(pc),a0
        clr.l   (a0)
        bra.w   release_publish_native

release_convert_wait:
        FSTAT   14
        bsr.w   release_buffer_wait
        FSTAT   15
        ifne FRAME_STATS
        cmpa.l  release_front(pc),a1
        beq.w   timing_bad      ; converter must never own the displayed buffer
        endif
release_convert_ready:
        rts

release_buffer_wait:
        tst.w   release_pending(pc)
        bne.s   release_buffer_wait
        rts

; The game may destroy its View/copper lists during modal/geometry transitions.
; Drain before native teardown; the IRQ still services a request when inactive.
release_teardown:
        bsr.w   release_buffer_wait
        move.l  a0,-(sp)
        lea     release_front(pc),a0
        clr.l   (a0)
        move.l  (sp)+,a0
        bra.w   release_teardown_native

release_input_vblank:
        bsr.w   release_vblank
        bra.l   timing_record_input

release_vblank:
        movem.l d0-d7/a0-a6,-(sp)
        move.w  ccr,-(sp)
        tst.w   release_pending(pc)
        beq.w   release_vblank_done
        move.l  timing_data(pc),a0
        move.l  D_7f02(a0),d0
        sub.l   release_pending_time(pc),d0
        bmi.w   release_vblank_done ; never show a future prediction early
release_vblank_early:
        bsr.w   release_beam
        cmpi.w  #4,d0            ; allow copinit's initial register/sprite setup
        blo.s   release_vblank_early
        cmpi.w  #12,d0           ; leave time for native pointer bookkeeping
        bhi.s   release_vblank_late
        move.l  release_pending_a4(pc),a4
        tst.w   A_m752(a4)         ; native publication lock must be idle (-1)
        bpl.s   release_vblank_late
        move.w  release_pending_index(pc),-(sp)
        move.l  timing_game(pc),a0
        jsr     E_33a12(a0)       ; native View/BitMap/COP2LC publication, no OS call
        addq.l  #2,sp
        bsr.w   release_beam
        cmpi.w  #16,d0           ; never restart the copper in the visible window
        bhi.s   release_vblank_late
        move.w  d0,$dff08a       ; COPJMP2: select the new list in this blank
release_presented:
        lea     release_front(pc),a0
        move.l  release_pending_plane(pc),(a0)
        ifne FRAME_STATS
        bsr.w   frame_stats_display
        endif
        lea     release_pending(pc),a0
        clr.w   (a0)            ; old front is now available to the converter
        bra.s   release_vblank_done
release_vblank_late:
        lea     release_late(pc),a0
        addq.l  #1,(a0)          ; retain request; retry next VBL
release_vblank_done:
        move.w  (sp)+,ccr
        movem.l (sp)+,d0-d7/a0-a6
        rts

release_beam:
        move.l  $dff004,d0
        move.l  $dff004,d1
        lsr.l   #8,d0
        lsr.l   #8,d1
        andi.w  #$1ff,d0
        andi.w  #$1ff,d1
        cmp.w   d0,d1
        bne.s   release_beam
        rts
        cnop 0,4
release_pending:       dc.w 0
release_pending_index: dc.w 0
release_pending_a4:    dc.l 0
release_pending_plane: dc.l 0
release_front:         dc.l 0
release_late:          dc.l 0
release_render_time:  dcb.l 4,0 ; target, clock sample, debt, selected fraction
release_pending_time: dcb.l 4,0 ; immutable until IRQ retires this picture
