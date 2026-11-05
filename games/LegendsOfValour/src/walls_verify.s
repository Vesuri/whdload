; VERIFY wall paired-loop twin: snapshot the entire allocated chunky column,
; run the runtime-copied original, restore input, then run the actual W3 block.
; Compare all output registers, CCR (including X) and all column bytes/unused rows.
; The original tail executes once, after comparison, with the W3 output restored.
_w3_verify_install
        movem.l d0-a6,-(sp)
        lea ($4c38,a0),a1
        lea (_w3_original,pc),a2
        moveq #15-1,d0
.copy   move.w (a1)+,(a2)+
        dbf d0,.copy
        move.w #$4e75,(a2)
        lea (_w3_twin_continue_0+2,pc),a1
        lea ($4c56,a0),a2
        move.l a2,(a1)
        lea (_w3_twin_continue_1+2,pc),a1
        lea ($4cfa,a0),a2
        move.l a2,(a1)
        lea (_w3_twin_continue_2+2,pc),a1
        lea ($4d7e,a0),a2
        move.l a2,(a1)
        lea (_w3_entry_0,pc),a1
        lea (_w3_optimized+0,pc),a2
        move.l a1,(a2)
        lea (_w3_twin_cleanup_0,pc),a1
        lea (_w3_continues+0,pc),a2
        move.l a1,(a2)
        lea (_w3_entry_1,pc),a1
        lea (_w3_optimized+4,pc),a2
        move.l a1,(a2)
        lea (_w3_twin_cleanup_1,pc),a1
        lea (_w3_continues+4,pc),a2
        move.l a1,(a2)
        lea (_w3_entry_2,pc),a1
        lea (_w3_optimized+8,pc),a2
        move.l a1,(a2)
        lea (_w3_twin_cleanup_2,pc),a1
        lea (_w3_continues+8,pc),a2
        move.l a1,(a2)
        movem.l (sp)+,d0-a6
        rts
_w3_twin_0
        movem.l d0-a6,-(sp)
_verify_sr_0 EQU *
        move.w sr,-(sp)
        move.w #0,-(sp)
        bra _w3_twin
_w3_twin_1
        movem.l d0-a6,-(sp)
_verify_sr_1 EQU *
        move.w sr,-(sp)
        move.w #1,-(sp)
        bra _w3_twin
_w3_twin_2
        movem.l d0-a6,-(sp)
_verify_sr_2 EQU *
        move.w sr,-(sp)
        move.w #2,-(sp)
        bra _w3_twin
_w3_twin
        move.l (_h11,pc),a0
        move.l ($5fc2,a0),a0
        move.l a5,d0
        sub.l a0,d0
        cmp.l #20000,d0
        bhs _w3_bad_column
        divu.w #192,d0
        swap d0
        and.l #$ffff,d0
        adda.l d0,a0
        lea (_w3_column,pc),a1
        move.l a0,(a1)
        move.w #104,(_w3_rows-_w3_column,a1)
        cmp.w #32,d0
        bhs .rows
        addq.w #1,(_w3_rows-_w3_column,a1)
.rows   lea (_w3_seed,pc),a1
        bsr _w3_save_column
        pea .original_done(pc)
        pea (_w3_original+24,pc)
        move.w (10,sp),ccr
        movem.l (12,sp),d0-a6
        rts
.original_done
        movem.l d0-a6,-(sp)
_verify_sr_3 EQU *
        move.w sr,-(sp)
        lea (_w3_expected,pc),a1
        bsr _w3_save_column
        lea (_w3_seed,pc),a1
        bsr _w3_restore_column
        ; The paired body is identical in all three original variants. Rotate
        ; the actual replacement block, so every block gets the same live inputs
        ; even when the route never chooses the third material tail.
        moveq #0,d0
        move.w (_w3_next,pc),d0
        lea (_w3_next,pc),a0
        move.w d0,(_w3_selected-_w3_next,a0)
        addq.w #1,(a0)
        cmp.w #3,(a0)
        blo .selected
        clr.w (a0)
.selected
        lsl.w #2,d0
        lea (_w3_optimized,pc),a0
        move.l (a0,d0.w),a0
        pea .optimized_done(pc)
        move.l a0,-(sp)
        move.w (72,sp),ccr
        movem.l (74,sp),d0-a6
        rts
.optimized_done
        movem.l d0-a6,-(sp)
_verify_sr_4 EQU *
        move.w sr,-(sp)
        move.w (sp),d0
        move.w (62,sp),d1
        eor.w d1,d0
        and.w #31,d0
        bne _w3_difference
        lea (2,sp),a0
        lea (64,sp),a1
        moveq #15-1,d0
.reg    cmpm.l (a0)+,(a1)+
        bne _w3_difference
        dbf d0,.reg
        move.l (_w3_column,pc),a0
        lea (_w3_expected,pc),a1
        move.w (_w3_rows,pc),d0
        subq.w #1,d0
.byte   move.b (a0),d1
        cmp.b (a1)+,d1
        bne _w3_difference
        lea (192,a0),a0
        dbf d0,.byte
        moveq #0,d0
        move.w (_w3_selected,pc),d0
        lsl.w #2,d0
        lea (_w3_cases,pc),a0
        addq.l #1,(a0,d0.w)
        moveq #0,d0
        move.w (124,sp),d0
        lsl.w #2,d0
        lea (_w3_counts,pc),a0
        addq.l #1,(a0,d0.w)
        lea (_w3_continues,pc),a0
        move.l (a0,d0.w),a0
        move.l a0,(124,sp)
        move.w (sp),ccr
        movem.l (2,sp),d0-a6
        lea (124,sp),sp
        rts
; Above RTS consumes the continuation saved over index/entry CCR; the remaining
; 60-byte input snapshot is dropped by the per-variant continuation wrapper.
_w3_twin_return rts
_w3_twin_cleanup_0
        lea (60,sp),sp
_w3_twin_continue_0 dc.w $4ef9
        dc.l 0
_w3_twin_cleanup_1
        lea (60,sp),sp
_w3_twin_continue_1 dc.w $4ef9
        dc.l 0
_w3_twin_cleanup_2
        lea (60,sp),sp
_w3_twin_continue_2 dc.w $4ef9
        dc.l 0
_w3_save_column
        move.l (_w3_column,pc),a0
        move.w (_w3_rows,pc),d0
        subq.w #1,d0
.copy   move.b (a0),(a1)+
        lea (192,a0),a0
        dbf d0,.copy
        rts
_w3_restore_column
        move.l (_w3_column,pc),a0
        move.w (_w3_rows,pc),d0
        subq.w #1,d0
.copy   move.b (a1)+,(a0)
        lea (192,a0),a0
        dbf d0,.copy
        rts
_w3_bad_column lea (_w3_badcolumn,pc),a0
        bra _c2p_abort
_w3_difference lea (_w3_diffmsg,pc),a0
        bra _c2p_abort
_w3_badcolumn dc.b "W3 twin: input outside chunky buffer",0
_w3_diffmsg dc.b "W3 twin: differing pixel, register or CCR",0
        EVEN
        CNOP 0,4
_w3_optimized ds.l 3
_w3_continues ds.l 3
_w3_counts ds.l 3
_w3_cases ds.l 3
_w3_next dc.w 0
_w3_selected dc.w 0
_w3_column dc.l 0
_w3_rows dc.w 0
_w3_original ds.b 32
_w3_seed ds.b 106
_w3_expected ds.b 106
        EVEN
