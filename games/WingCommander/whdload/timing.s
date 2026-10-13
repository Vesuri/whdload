; Experimental English CUSTOM1=3 simulation adapter. Not a completed phase-9
; implementation until player/input/presentation dependencies pass their gates.
; Original language choices CUSTOM1=0/1 install no new game patches.
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

; This initial integration keeps native input on each world update. The
; responsive player path is added separately before the phase-9 gate.
timing_loop:
        movem.l d0-d7/a0-a6,-(sp)
        lea     timing_active(pc),a0
        move.w  #1,(a0)
        ; First native update loads flight assets; it establishes the epoch.
        bsr.w   timing_native_input
        tst.w   -32628(a4)
        bne.w   timing_leave
        bsr.w   timing_world
        lea     timing_abort(pc),a0
        clr.w   (a0)
        bsr.w   timing_rebase
.loop:
        tst.w   -32628(a4)
        bne.w   timing_leave
        move.l  -252(a4),d0           ; D:7f02 native VBL counter
        move.l  timing_hz(pc),d1
        moveq   #1,d2
        lea     timing_clock(pc),a0
        bsr.w   timing_advance
        move.l  d0,d6
.ticks:
        tst.l   d6
        beq.s   .draw
        bsr.w   timing_native_input
        tst.w   -32628(a4)
        bne.w   timing_leave
        tst.w   timing_abort(pc)
        bne.s   .cancel
        bsr.w   timing_world
        subq.l  #1,d6
        bra.s   .ticks
.cancel:
        lea     timing_abort(pc),a0
        clr.w   (a0)
        lea     timing_clock(pc),a0
        sub.l   d6,12(a0)
        move.l  d6,d0
        mulu.w  timing_hz+2(pc),d0
        add.l   d0,16(a0)
.draw:
        move.l  timing_game(pc),a6
        jsr     $510(a6)
        move.l  timing_game(pc),a6
        jsr     $46e6(a6)
        bra.s   .loop

timing_native_input:
        move.l  timing_game(pc),a6
        jsr     $19330(a6)
        cmpi.w  #-1,d0
        bne.s   .done
        move.w  #5,-32628(a4)
.done:
        rts

timing_world:
        move.l  timing_game(pc),a6
        jsr     $2a8(a6)
timing_world_done:
        lea     timing_completed(pc),a0
        addq.l  #1,(a0)
        rts

timing_rebase:
        movem.l d0-d3/a0,-(sp)
        move.l  -252(a4),d0
        move.l  timing_hz(pc),d1
        moveq   #0,d2
        lea     timing_clock(pc),a0
        bsr.w   timing_advance
        move.l  -252(a4),d0
        move.l  timing_hz(pc),d1
        moveq   #1,d2
        bsr.w   timing_advance
        movem.l (sp)+,d0-d3/a0
        rts

timing_leave:
        lea     timing_active(pc),a0
        clr.w   (a0)
        bsr.s   timing_rebase
        movem.l (sp)+,d0-d7/a0-a6
        move.l  timing_exit(pc),-(sp)
        rts

timing_pause:
        move.l  a6,-(sp)
        move.l  timing_game(pc),a6
        jsr     $878(a6)
        move.w  ccr,-(sp)
        bsr.w   timing_rebase
        move.l  a0,-(sp)
        lea     timing_abort(pc),a0
        move.w  #1,(a0)
        move.l  (sp)+,a0
        move.w  (sp)+,ccr
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
