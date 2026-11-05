; VERIFY sprite-loop twin: snapshot the entire allocated chunky column,
; run the runtime-copied original, restore input, then run the actual W4 block.
; Compare all output registers, CCR (including X) and all column bytes/unused rows.
; The original column tail executes once, after comparison, with the W4 output restored.
_w4_verify_install
        movem.l d0-a6,-(sp)
        lea ($517e,a0),a1
        lea (_w4_original_0,pc),a2
        moveq #10-1,d0
.copy0 move.w (a1)+,(a2)+
        dbf d0,.copy0
        move.w #$4e75,(a2)
        lea (_w4_twin_continue_0+2,pc),a1
        lea ($5192,a0),a2
        move.l a2,(a1)
        lea (_w4_original_0,pc),a1
        lea (_w4_originals+0,pc),a2
        move.l a1,(a2)
        lea (_w4_entry_0,pc),a1
        lea (_w4_optimized+0,pc),a2
        move.l a1,(a2)
        lea (_w4_twin_cleanup_0,pc),a1
        lea (_w4_continues+0,pc),a2
        move.l a1,(a2)
        move.l a0,a1
        adda.l #$9452,a1
        lea (_w4_original_1,pc),a2
        moveq #11-1,d0
.copy1 move.w (a1)+,(a2)+
        dbf d0,.copy1
        move.w #$4e75,(a2)
        lea (_w4_twin_continue_1+2,pc),a1
        move.l a0,a2
        adda.l #$9468,a2
        move.l a2,(a1)
        lea (_w4_original_1,pc),a1
        lea (_w4_originals+4,pc),a2
        move.l a1,(a2)
        lea (_w4_entry_1,pc),a1
        lea (_w4_optimized+4,pc),a2
        move.l a1,(a2)
        lea (_w4_twin_cleanup_1,pc),a1
        lea (_w4_continues+4,pc),a2
        move.l a1,(a2)
        move.l a0,a1
        adda.l #$94e2,a1
        lea (_w4_original_2,pc),a2
        moveq #11-1,d0
.copy2 move.w (a1)+,(a2)+
        dbf d0,.copy2
        move.w #$4e75,(a2)
        lea (_w4_twin_continue_2+2,pc),a1
        move.l a0,a2
        adda.l #$94f8,a2
        move.l a2,(a1)
        lea (_w4_original_2,pc),a1
        lea (_w4_originals+8,pc),a2
        move.l a1,(a2)
        lea (_w4_entry_2,pc),a1
        lea (_w4_optimized+8,pc),a2
        move.l a1,(a2)
        lea (_w4_twin_cleanup_2,pc),a1
        lea (_w4_continues+8,pc),a2
        move.l a1,(a2)
        movem.l (sp)+,d0-a6
        rts
_w4_twin_0
        movem.l d0-a6,-(sp)
_verify_sr_5 EQU *
        move.w sr,-(sp)
        move.w #0,-(sp)
        bra _w4_twin
_w4_twin_1
        movem.l d0-a6,-(sp)
_verify_sr_6 EQU *
        move.w sr,-(sp)
        move.w #1,-(sp)
        bra _w4_twin
_w4_twin_2
        movem.l d0-a6,-(sp)
_verify_sr_7 EQU *
        move.w sr,-(sp)
        move.w #2,-(sp)
        bra _w4_twin
_w4_twin
        move.l (_h11,pc),a0
        move.l ($5fc2,a0),a0
        move.l (36,sp),d0
        sub.l a0,d0
        cmp.l #20000,d0
        bhs _w4_bad_column
        divu.w #192,d0
        swap d0
        and.l #$ffff,d0
        adda.l d0,a0
        lea (_w4_column,pc),a1
        move.l a0,(a1)
        move.w #104,(_w4_rows-_w4_column,a1)
        cmp.w #32,d0
        bhs .rows
        addq.w #1,(_w4_rows-_w4_column,a1)
.rows   lea (_w4_seed,pc),a1
        bsr _w4_save_column
        moveq #0,d0
        move.w (sp),d0
        lsl.w #2,d0
        lea (_w4_originals,pc),a0
        move.l (a0,d0.w),a0
        pea .original_done(pc)
        move.l a0,-(sp)
        move.w (10,sp),ccr
        movem.l (12,sp),d0-a6
        rts
.original_done
        movem.l d0-a6,-(sp)
_verify_sr_8 EQU *
        move.w sr,-(sp)
        lea (_w4_expected,pc),a1
        bsr _w4_save_column
        lea (_w4_seed,pc),a1
        bsr _w4_restore_column
        moveq #0,d0
        move.w (62,sp),d0
        beq .selected
        ; The two remapped bodies are identical. Alternate their replacements
        ; with real palette/texture inputs, retaining the original column tail.
        lea (_w4_next,pc),a0
        move.w (a0),d0
        eori.w #1,(a0)
        addq.w #1,d0
.selected
        lea (_w4_selected,pc),a0
        move.w d0,(a0)
        lsl.w #2,d0
        lea (_w4_optimized,pc),a0
        move.l (a0,d0.w),a0
        pea .optimized_done(pc)
        move.l a0,-(sp)
        move.w (72,sp),ccr
        movem.l (74,sp),d0-a6
        rts
.optimized_done
        movem.l d0-a6,-(sp)
_verify_sr_9 EQU *
        move.w sr,-(sp)
        move.w (sp),d0
        move.w (62,sp),d1
        eor.w d1,d0
        and.w #31,d0
        bne _w4_difference
        lea (2,sp),a0
        lea (64,sp),a1
        moveq #15-1,d0
.reg    cmpm.l (a0)+,(a1)+
        bne _w4_difference
        dbf d0,.reg
        move.l (_w4_column,pc),a0
        lea (_w4_expected,pc),a1
        move.w (_w4_rows,pc),d0
        subq.w #1,d0
.byte   move.b (a0),d1
        cmp.b (a1)+,d1
        bne _w4_difference
        lea (192,a0),a0
        dbf d0,.byte
        moveq #0,d0
        move.w (_w4_selected,pc),d0
        lsl.w #2,d0
        lea (_w4_cases,pc),a0
        addq.l #1,(a0,d0.w)
        moveq #0,d0
        move.w (124,sp),d0
        lsl.w #2,d0
        lea (_w4_counts,pc),a0
        addq.l #1,(a0,d0.w)
        lea (_w4_continues,pc),a0
        move.l (a0,d0.w),a0
        move.l a0,(124,sp)
        move.w (sp),ccr
        movem.l (2,sp),d0-a6
        lea (124,sp),sp
        rts
; Above RTS consumes the continuation saved over index/entry CCR; the remaining
; 60-byte input snapshot is dropped by the per-variant continuation wrapper.
_w4_twin_return rts
_w4_twin_cleanup_0
        lea (60,sp),sp
_w4_twin_continue_0 dc.w $4ef9
        dc.l 0
_w4_twin_cleanup_1
        lea (60,sp),sp
_w4_twin_continue_1 dc.w $4ef9
        dc.l 0
_w4_twin_cleanup_2
        lea (60,sp),sp
_w4_twin_continue_2 dc.w $4ef9
        dc.l 0
_w4_save_column
        move.l (_w4_column,pc),a0
        move.w (_w4_rows,pc),d0
        subq.w #1,d0
.copy   move.b (a0),(a1)+
        lea (192,a0),a0
        dbf d0,.copy
        rts
_w4_restore_column
        move.l (_w4_column,pc),a0
        move.w (_w4_rows,pc),d0
        subq.w #1,d0
.copy   move.b (a1)+,(a0)
        lea (192,a0),a0
        dbf d0,.copy
        rts
_w4_bad_column lea (_w4_badcolumn,pc),a0
        bra _c2p_abort
_w4_difference lea (_w4_diffmsg,pc),a0
        bra _c2p_abort
_w4_badcolumn dc.b "W4 twin: input outside chunky buffer",0
_w4_diffmsg dc.b "W4 twin: differing pixel, register or CCR",0
        EVEN
        CNOP 0,4
_w4_optimized ds.l 3
_w4_continues ds.l 3
_w4_counts ds.l 3
_w4_cases ds.l 3
_w4_next dc.w 0
_w4_selected dc.w 0
_w4_column dc.l 0
_w4_rows dc.w 0
_w4_originals ds.l 3
_w4_original_0 ds.b 32
_w4_original_1 ds.b 32
_w4_original_2 ds.b 32
_w4_seed ds.b 106
_w4_expected ds.b 106
        EVEN
