; W6: clear fixed-width rows backwards with MOVEM blocks. The sky/floor caller,
; colour construction, row count and 192-byte stride are unchanged.
_w6_install
        movem.l d0-a6,-(sp)
        move.l (_custom2,pc),d0
        btst #5,d0
        beq .done
        move.l (_custom1,pc),d0
        tst.l d0
        bne .done
        move.l (_h12,pc),a0
        cmp.w #$3239,($51ee,a0)
        bne .bad
        lea ($36,a0),a1
        cmp.l ($51f0,a0),a1
        bne .bad
        IFD VERIFY
        lea ($51ee,a0),a1
        lea (_w6_original,pc),a2
        moveq #22-1,d0
.copy   move.w (a1)+,(a2)+
        dbf d0,.copy
        ENDC
        lea (_w6_clear,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #7,d0
        beq .normal
        lea (_w6_twin,pc),a1
.normal
        ENDC
        ; PERF_RANGE h12:051ee 6 bit=5
        move.w #$4ef9,($51ee,a0)
        move.l a1,($51f0,a0)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
.done   movem.l (sp)+,d0-a6
        rts
.bad    lea (_w6_badcode,pc),a0
        bra _c2p_abort
_w6_badcode dc.b "W6: unexpected chunky clear",0
        EVEN
_w6_clear
        ; Use large fixed blocks for the game's three widths. Retain the
        ; general 16-byte path for other widths, with the original rounding.
        movem.l d2-d7/a2-a6,-(sp)
        move.l (_h12,pc),a2
        move.w ($36,a2),d1
        subq.w #1,d1
        move.w ($2e,a2),d3
        lsr.w #4,d3
        subq.w #1,d3
        cmp.w #11,d3
        beq .large
        cmp.w #6,d3
        beq .medium
        cmp.w #4,d3
        beq .small
        movem.l (sp)+,d2-d7/a2-a6
        bra _w6_clear_fallback
.large
        bsr .colour
.large_row
        lea (192,a0),a1
        movem.l d2-d7/a2-a6,-(a1)
        movem.l d2-d7/a2-a6,-(a1)
        movem.l d2-d7/a2-a6,-(a1)
        movem.l d2-d7/a2-a6,-(a1)
        movem.l d2-d5,-(a1)
        lea (192,a0),a0
        dbf d1,.large_row
        lea (192,a1),a1
        movem.l (sp)+,d2-d7/a2-a6
        move.w #11,d3
        bra .finish
.medium
        bsr .colour
.medium_row
        lea (112,a0),a1
        movem.l d2-d7/a2-a6,-(a1)
        movem.l d2-d7/a2-a6,-(a1)
        movem.l d2-d7,-(a1)
        lea (192,a0),a0
        dbf d1,.medium_row
        lea (112,a1),a1
        movem.l (sp)+,d2-d7/a2-a6
        move.w #6,d3
        bra .finish
.small
        bsr .colour
.small_row
        lea (80,a0),a1
        movem.l d2-d7/a2-a6,-(a1)
        movem.l d2-d7/a2-a4,-(a1)
        lea (192,a0),a0
        dbf d1,.small_row
        lea (80,a1),a1
        movem.l (sp)+,d2-d7/a2-a6
        move.w #4,d3
.finish
        move.w #-1,d2
        tst.l d0
        rts
.colour
        move.l d0,d2
        move.l d0,d3
        move.l d0,d4
        move.l d0,d5
        move.l d0,d6
        move.l d0,d7
        move.l d0,a2
        move.l d0,a3
        move.l d0,a4
        move.l d0,a5
        move.l d0,a6
        rts
_w6_clear_fallback
        movem.l d4-d7/a2,-(sp)
        move.l (_h12,pc),a2
        move.w ($36,a2),d1
        subq.w #1,d1
        move.w ($2e,a2),d3
        lsr.w #4,d3
        subq.w #1,d3
        moveq #0,d4
        move.w d3,d4
        lsl.w #4,d4
        move.l d4,a2
        lea (16,a2),a2
        move.l d0,d4
        move.l d0,d5
        move.l d0,d6
        move.l d0,d7
.row    move.l a0,a1
        adda.l a2,a1
        move.w d3,d2
.block  movem.l d4-d7,-(a1)
        dbf d2,.block
        lea (192,a0),a0
        dbf d1,.row
        adda.l a2,a1
        tst.l d0
        movem.l (sp)+,d4-d7/a2
        rts
        IFD VERIFY
        INCLUDE clear_verify.s
        ENDC
