; Original and replacement clears run with identical registers. Clearing has no
; input-pixel dependency: retain the original's entire 20,000-byte result, then
; compare after the replacement, including all untouched rows and columns.
_w6_twin
        movem.l d0-a6,-(sp)
_verify_sr_10 EQU *
        move.w sr,-(sp)
        pea .original_done(pc)
        pea (_w6_original,pc)
        move.w (8,sp),ccr
        movem.l (10,sp),d0-a6
        rts
.original_done
        movem.l d0-a6,-(sp)
_verify_sr_11 EQU *
        move.w sr,-(sp)
        move.l (_h11,pc),a0
        move.l (h11_05fc2,a0),a0
        lea (_c2p_function,pc),a1
        adda.l #_c2p_chunky-_c2p_function,a1
        move.w #5000-1,d0
.copy   move.l (a0)+,(a1)+
        dbf d0,.copy
        pea .optimized_done(pc)
        pea (_w6_clear,pc)
        move.w (70,sp),ccr
        movem.l (72,sp),d0-a6
        rts
.optimized_done
        movem.l d0-a6,-(sp)
_verify_sr_12 EQU *
        move.w sr,-(sp)
        move.w (sp),d0
        move.w (62,sp),d1
        eor.w d1,d0
        and.w #31,d0
        bne .different
        lea (2,sp),a0
        lea (64,sp),a1
        moveq #15-1,d0
.reg    cmpm.l (a0)+,(a1)+
        bne .different
        dbf d0,.reg
        move.l (_h11,pc),a0
        move.l (h11_05fc2,a0),a0
        lea (_c2p_function,pc),a1
        adda.l #_c2p_chunky-_c2p_function,a1
        move.w #5000-1,d0
.pixel  cmpm.l (a0)+,(a1)+
        bne .different
        dbf d0,.pixel
        lea (_w6_tests,pc),a0
        addq.l #1,(a0)
        move.l (_h12,pc),a0
        move.w (h12_0002e,a0),d0
        lea (_w6_counts,pc),a0
        cmp.w #192,d0
        beq .count
        addq.l #4,a0
        cmp.w #112,d0
        beq .count
        addq.l #4,a0
        cmp.w #80,d0
        bne .restore
.count  addq.l #1,(a0)
.restore
        move.w (sp),ccr
        movem.l (2,sp),d0-a6
        lea (186,sp),sp
        rts
.different lea (_w6_diffmsg,pc),a0
        bra _c2p_abort
_w6_diffmsg dc.b "W6 twin: differing pixel, register or CCR",0
        EVEN
_w6_tests dc.l 0
_w6_counts ds.l 3
_w6_original ds.b 44
