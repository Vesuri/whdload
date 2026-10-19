; Shared opening motion policy. Variant offsets and displaced instructions are
; generated from pinned inputs into tmp/, never copied into this source.
; Orchestra steps are 10 Hz, fireworks every three fields. Zooms sample per field.
opening_begin:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w timing_rate
        lea opening_hz(pc),a0
        move.w d0,(a0)
        lea opening_active(pc),a0
        move.w #1,(a0)
        movem.l (sp)+,d0-d7/a0-a6
        bra.w opening_rebase
opening_end:
        movem.l d0/a0,-(sp)
        lea opening_active(pc),a0
        clr.w (a0)
        movem.l (sp)+,d0/a0
        rts
opening_rebase:
        movem.l d0/a0,-(sp)
        move.l OPEN_FIELD(a4),d0
        lea opening_epoch(pc),a0
        move.l d0,(a0)+
        move.l d0,(a0)+          ; last sampled field
        move.l d0,(a0)+          ; next animation cursor
        movem.l (sp)+,d0/a0
        rts

; Keep input polling responsive while waiting; do not advance a native script
; index, consume RNG or allocate a particle on a presentation-only field.
opening_fireworks_input:
        movem.l d1-d7/a0-a6,-(sp)
        moveq #3,d2
        bra.s opening_tick_wait
opening_tick_input:
        movem.l d1-d7/a0-a6,-(sp)
        moveq #0,d2
        move.w opening_hz(pc),d2
        divu.w #10,d2
opening_tick_wait:
.wait:
        bsr.w opening_input_native
        tst.w d0
        bne.s .done
        move.l OPEN_FIELD(a4),d1
        sub.l opening_cursor(pc),d1
        cmp.l d2,d1
        bcs.s .wait
        lea opening_cursor(pc),a0
        add.l d2,(a0)            ; retain debt; never discard script steps
.done:
        move.w #1,OPEN_COUNTDOWN(a4)
        movem.l (sp)+,d1-d7/a0-a6
        rts

; D0 = elapsed fields, at most 3600 (the bounded zooms finish within seconds).
; Subtraction is modulo 2^32, so an ordinary counter wrap is harmless.
opening_sample:
        move.l OPEN_FIELD(a4),d0
        cmp.l opening_last(pc),d0
        beq.s opening_sample
        lea opening_last(pc),a0
        move.l d0,(a0)
        sub.l opening_epoch(pc),d0
        cmpi.l #3600,d0
        bls.s .ready
        move.l #3600,d0
.ready:
        rts

; Native separation grows s -> s + floor(s/4) + 1 per logical step.
; Evaluate that trajectory at 10 Hz, then interpolate its current interval for
; display only. No global geometry, RNG or music state is extrapolated.
opening_separation_sample:
        movem.l d0-d1/d3-d7/a0,-(sp)
        bsr.w opening_sample
        mulu.w #10,d0
        divu.w opening_hz(pc),d0
        move.w d0,d3            ; whole steps
        swap d0
        move.w d0,d4            ; fractional numerator in fields*10
        moveq #1,d2
.steps:
        tst.w d3
        beq.s .fraction
        move.w d2,d0
        lsr.w #2,d0
        addq.w #1,d0
        add.w d0,d2
        cmpi.w #120,d2
        bhs.s .done
        subq.w #1,d3
        bra.s .steps
.fraction:
        move.w d2,d0
        lsr.w #2,d0
        addq.w #1,d0
        mulu.w d4,d0
        divu.w opening_hz(pc),d0
        add.w d0,d2
.done:
        move.w #1,OPEN_COUNTDOWN(a4)
        movem.l (sp)+,d0-d1/d3-d7/a0
        rts

; Native flight projects depth in 100-unit logo / 200-unit planet samples.
; One 100-unit step is one 10 Hz motion tick. Recompute the original projection
; each displayed field instead of repeating stale projected coordinates.
opening_flight_prepare:
        cmpi.w #5000,d3
        bne.s .ready
        moveq #57,d2
.ready:
        clr.w d5
        clr.w d6
        moveq #0,d7
        move.w #1,OPEN_COUNTDOWN(a4)
        rts
opening_flight_sample:
        movem.l d0-d1/d4-d7/a0,-(sp)
        bsr.w opening_sample
        cmpi.l #300,d0
        bls.s .bounded
        move.l #300,d0
.bounded:
        mulu.w #1000,d0
        divu.w opening_hz(pc),d0
        andi.l #$ffff,d0
        cmpi.w #4001,d0
        bls.s .depth
        move.w #4001,d0
.depth:
        move.w #5000,d3
        sub.w d0,d3
        ; Preserve native vertical trajectory: -2 per 100 units until the
        ; 3000 crossing, then +2. Fractional fields produce pixel increments.
        moveq #0,d1
        move.w d0,d1
        cmpi.w #1900,d1
        bls.s .approach
        subi.w #1900,d1
        divu.w #50,d1
        moveq #19,d2
        add.w d1,d2
        bra.s .done
.approach:
        divu.w #50,d1
        moveq #57,d2
        sub.w d1,d2
.done:
        movem.l (sp)+,d0-d1/d4-d7/a0
        rts

opening_input_native: jmp $0
opening_active: dc.w 0
opening_hz: dc.w 50
opening_epoch: dc.l 0
opening_last: dc.l 0
opening_cursor: dc.l 0
