; Flight-only changed-block c2p. Original cache policy and nonflight paths remain.
; Each planar destination has its own last-source image in MEMF_FAST storage.
flight_render_entry:
        movem.l d0-a6,-(sp)
        FSTAT   9
        move.l  slave+$1de4(pc),d7
        cmpi.l  #3,d7
        bne.w   flight_render_original
        tst.w   timing_active(pc)
        beq.w   flight_render_invalidate
        cmpi.w  #200,d3
        bne.w   flight_render_invalidate
        cmpi.w  #320,d0
        bne.w   flight_render_invalidate
        move.l  flight_history(pc),d7
        bmi.w   flight_render_original
        bne.s   .ready
        bra.w   flight_render_original
.ready:
        move.l  slave+$1e04(pc),d7
        subq.l  #1,d7
        beq.s   .work
        FSTAT   10
        bsr.w   slave+$17b8
        FSTAT   11
.work:
flight_render_work:
        FSTAT   12
        lea     flight_destinations(pc),a3
        move.l  flight_history(pc),a2
        moveq   #1,d7
        cmpa.l  (a3),a1
        beq.s   .found
        adda.l  #64000,a2
        cmpa.l  4(a3),a1
        beq.s   .found
        ; A new destination always receives a full conversion. Rotating two
        ; records also handles a changed/reallocated display conservatively.
        move.l  4(a3),(a3)
        move.l  a1,4(a3)
        ; History 1 becomes history 0 logically by exchanging their pointers.
        lea     flight_history_order(pc),a6
        eori.w  #1,(a6)
        moveq   #0,d7
.found:
        ; Record 0/1 physical histories exchange whenever a new buffer appears.
        cmpa.l  (a3),a1
        seq     d0
        andi.w  #1,d0
        move.w  flight_history_order(pc),d1
        eor.w   d1,d0
        move.l  flight_history(pc),a2
        tst.w   d0
        beq.s   .history
        adda.l  #64000,a2
.history:
        ifne FLIGHT_CONTROL
        moveq   #0,d7
        else
        nop
        endif
        bsr.w   flight_delta
flight_render_work_done:
        FSTAT   13
        ifne FLIGHT_VERIFY
        move.l  32(sp),a0
        move.l  flight_reference(pc),a1
flight_reference_work:
        bsr.w   slave+$1ac6
flight_reference_done:
        move.l  36(sp),a0
        move.l  flight_reference(pc),a1
        move.w  #15999,d0
.check:
        cmpm.l  (a0)+,(a1)+
        bne.w   timing_bad
        dbf     d0,.check
        lea     flight_verified(pc),a0
        addq.l  #1,(a0)
        endif
        ; Same safe display-end publication policy as phase 6.
        FSTAT   14
        move.l  48(sp),a4
        lea     -660(a4),a0
        move.l  -778(a4),a6
        jsr     -402(a6)
        FSTAT   15
        movem.l (sp)+,d0-a6
        rts
flight_render_invalidate:
        lea     flight_destinations(pc),a3
        clr.l   (a3)+
        clr.l   (a3)
flight_render_original:
        bra.w   slave+$178e

; a0 source, a1 planar, a2 history, d7 valid. Checked against native full output.
flight_delta:
        movem.l d2-a6,-(sp)
        move.l  a0,a3
        move.l  a1,a4
        move.l  a2,a5
        tst.w   d7
        bne.s   .delta
        movem.l a3/a5,-(sp)
        bsr.w   slave+$1ac6
        movem.l (sp)+,a3/a5
        move.w  #15999,d6
.copy:
        move.l  (a3)+,(a5)+
        dbf     d6,.copy
        bra.w   .done
.delta:
        move.w  #1999,d6
.block:
FLIGHT_COMPARE_BLOCK
        bra.s   .next
.changed:
FLIGHT_COPY_BLOCK
        move.l  a3,a0
        move.l  a4,a1
        bsr.w   flight_kalms_block
.next:
        lea     32(a3),a3
        lea     32(a5),a5
        addq.l  #4,a4
        dbf     d6,.block
.done:
        movem.l (sp)+,d2-a6
        rts
        cnop 0,4
flight_history: dc.l 0
flight_destinations: dc.l 0,0
flight_history_order: dc.w 0
        ifne FLIGHT_VERIFY
flight_verified: dc.l 0
flight_reference: dc.l 0
        endif

; Allocate before the game takes its FAST heap, not at first flight conversion.
flight_render_init:
        movem.l d0-d1/a0-a1/a6,-(sp)
        move.l  #128000,d0
        move.l  #$10005,d1       ; MEMF_CLEAR | MEMF_FAST | MEMF_PUBLIC
        move.l  $4.w,a6
        jsr     -198(a6)
        lea     flight_history(pc),a0
        move.l  d0,(a0)
        bne.s   .allocated
        move.l  #-1,(a0)        ; no memory: retain original converter
.allocated:
        ifne FRAME_STATS
        bsr.w   frame_stats_init
        endif
        ifne FLIGHT_VERIFY
        move.l  #64000,d0
        move.l  #$10003,d1       ; CHIP reference: compare equal memory classes
        move.l  $4.w,a6
        jsr     -198(a6)
        lea     flight_reference(pc),a0
        move.l  d0,(a0)
        bne.s   .reference_ready
        lea     flight_history(pc),a0
        move.l  #-1,(a0)
.reference_ready:
        endif
        movem.l (sp)+,d0-d1/a0-a1/a6
        rts
