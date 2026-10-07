; VERIFY-only coupling experiment. Both runs install identical instrumentation;
; CUSTOM5 bit 8 adds eight PAL fields before each renderer entry after the anchor.
; No simulation timing is changed. Never included in normal or performance builds.
_timing_study_install
        movem.l d0-a6,-(sp)
        move.l (_h12,pc),a0
        cmp.l #$48e73f3e,($27bc,a0)
        bne .bad
        cmp.l #$6100fc14,($27c0,a0)
        bne .bad
        move.w #$4ef9,($27bc,a0)
        lea (_timing_study_render,pc),a1
        move.l a1,($27be,a0)
        move.w #$4e71,($27c2,a0)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
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
        move.l (_custom5,pc),d0
        btst #8,d0
        beq .restore
        move.l (_h11,pc),a0
        move.w ($602e,a0),d1
.wait   move.w ($602e,a0),d0
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
        add.l #$23d6,(sp)
        rts
.prepared
        move.l (_h12,pc),-(sp)
        add.l #$27c4,(sp)
        rts
_timing_study_bad dc.b "TIMING study: unexpected renderer entry",0
        EVEN
_timing_study_armed dc.w 0
_timing_study_delays dc.l 0
