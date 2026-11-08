; W4: eight sprite rows per block with one counter test per block.
; Address arithmetic preserves X; TST restores the last pixel flags on exit.
; Select this on 68000/10; 68020+ keep the original compact loop.
_w4_install
        movem.l d0-a6,-(sp)
        move.l (_custom2,pc),d0
        btst #3,d0
        beq .done
        move.l (_lov_attnflags,pc),d0
        btst #1,d0              ; AFB_68020
        beq .cpu_ok
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #5,d0              ; pixel twin may exercise either CPU
        bne .cpu_ok
        ENDC
        bra .done
.cpu_ok
        move.l (_custom1,pc),d0
        tst.l d0
        bne .done
        move.l (_h12,pc),a0
        cmp.l #$301d1033,(h12_0517e,a0)
        bne .bad
        tst.w (h12_05182,a0)
        bne .bad
        move.l a0,a4
        adda.l #h12_09452,a4
        cmp.l #$301d1a33,(a4)
        bne .bad
        move.l a0,a4
        adda.l #h12_09456,a4
        tst.w (a4)
        bne .bad
        move.l a0,a4
        adda.l #h12_094e2,a4
        cmp.l #$301d1a33,(a4)
        bne .bad
        move.l a0,a4
        adda.l #h12_094e6,a4
        tst.w (a4)
        bne .bad
        IFD VERIFY
        bsr _w4_verify_install
        ENDC
        lea (_w4_resume_0+2,pc),a1
        lea (h12_05192,a0),a2
        move.l a2,(a1)
        lea (_w4_entry_0,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #5,d0
        beq .normal0
        lea (_w4_twin_return,pc),a2
        lea (_w4_resume_0+2,pc),a3
        move.l a2,(a3)
        lea (_w4_twin_0,pc),a1
.normal0
        ENDC
        ; PERF_RANGE h12:0517e 6 bit=3
        move.w #$4ef9,(h12_0517e,a0)
        move.l a1,(h12_05180,a0)
        lea (_w4_resume_1+2,pc),a1
        move.l a0,a2
        adda.l #h12_09468,a2
        move.l a2,(a1)
        lea (_w4_entry_1,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #5,d0
        beq .normal1
        lea (_w4_twin_return,pc),a2
        lea (_w4_resume_1+2,pc),a3
        move.l a2,(a3)
        lea (_w4_twin_1,pc),a1
.normal1
        ENDC
        ; PERF_RANGE h12:09452 6 bit=3
        move.l a0,a4
        adda.l #h12_09452,a4
        move.w #$4ef9,(a4)
        move.l a0,a4
        adda.l #h12_09454,a4
        move.l a1,(a4)
        lea (_w4_resume_2+2,pc),a1
        move.l a0,a2
        adda.l #h12_094f8,a2
        move.l a2,(a1)
        lea (_w4_entry_2,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #5,d0
        beq .normal2
        lea (_w4_twin_return,pc),a2
        lea (_w4_resume_2+2,pc),a3
        move.l a2,(a3)
        lea (_w4_twin_2,pc),a1
.normal2
        ENDC
        ; PERF_RANGE h12:094e2 6 bit=3
        move.l a0,a4
        adda.l #h12_094e2,a4
        move.w #$4ef9,(a4)
        move.l a0,a4
        adda.l #h12_094e4,a4
        move.l a1,(a4)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
.done   movem.l (sp)+,d0-a6
        rts
.bad    lea (_w4_badcode,pc),a0
        bra _c2p_abort
_w4_badcode dc.b "W4: unexpected sprite-column loop",0
        EVEN
_w4_entry_0
        move.l a1,-(sp)
        cmp.w #7,d2
        bge _w4_chunk_0
        bra _w4_tail_0
_w4_chunk_0
_w4_row_0_0
        move.w (a5)+,d0
        move.b (a3,d0.w),d0
        and.b d6,d0
        beq .transparent_w4_row_0_0
        move.b d0,(a0)
.transparent_w4_row_0_0
_w4_row_0_1
        move.w (a5)+,d0
        move.b (a3,d0.w),d0
        and.b d6,d0
        beq .transparent_w4_row_0_1
        move.b d0,(192,a0)
.transparent_w4_row_0_1
_w4_row_0_2
        move.w (a5)+,d0
        move.b (a3,d0.w),d0
        and.b d6,d0
        beq .transparent_w4_row_0_2
        move.b d0,(384,a0)
.transparent_w4_row_0_2
_w4_row_0_3
        move.w (a5)+,d0
        move.b (a3,d0.w),d0
        and.b d6,d0
        beq .transparent_w4_row_0_3
        move.b d0,(576,a0)
.transparent_w4_row_0_3
_w4_row_0_4
        move.w (a5)+,d0
        move.b (a3,d0.w),d0
        and.b d6,d0
        beq .transparent_w4_row_0_4
        move.b d0,(768,a0)
.transparent_w4_row_0_4
_w4_row_0_5
        move.w (a5)+,d0
        move.b (a3,d0.w),d0
        and.b d6,d0
        beq .transparent_w4_row_0_5
        move.b d0,(960,a0)
.transparent_w4_row_0_5
_w4_row_0_6
        move.w (a5)+,d0
        move.b (a3,d0.w),d0
        and.b d6,d0
        beq .transparent_w4_row_0_6
        move.b d0,(1152,a0)
.transparent_w4_row_0_6
_w4_row_0_7
        move.w (a5)+,d0
        move.b (a3,d0.w),d0
        and.b d6,d0
        beq .transparent_w4_row_0_7
        move.b d0,(1344,a0)
.transparent_w4_row_0_7
        lea (1536,a0),a0
        move.w d2,a1
        suba.w #8,a1
        move.w a1,d2
        cmp.w #7,d2
        bge _w4_chunk_0
        tst.w d2
        bmi _w4_done_0
_w4_tail_0
_w4_row_0_8
        move.w (a5)+,d0
        move.b (a3,d0.w),d0
        and.b d6,d0
        beq .transparent_w4_row_0_8
        move.b d0,(a0)
.transparent_w4_row_0_8
        lea (192,a0),a0
        dbf d2,_w4_tail_0
_w4_done_0
        move.l (sp)+,a1
        tst.b d0
        bra _w4_resume_0
_w4_resume_0 dc.w $4ef9
        dc.l 0

_w4_entry_1
        move.l a1,-(sp)
        cmp.w #7,d2
        bge _w4_chunk_1
        bra _w4_tail_1
_w4_chunk_1
_w4_row_1_0
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_1_0
        move.b d5,(a0)
.transparent_w4_row_1_0
_w4_row_1_1
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_1_1
        move.b d5,(192,a0)
.transparent_w4_row_1_1
_w4_row_1_2
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_1_2
        move.b d5,(384,a0)
.transparent_w4_row_1_2
_w4_row_1_3
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_1_3
        move.b d5,(576,a0)
.transparent_w4_row_1_3
_w4_row_1_4
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_1_4
        move.b d5,(768,a0)
.transparent_w4_row_1_4
_w4_row_1_5
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_1_5
        move.b d5,(960,a0)
.transparent_w4_row_1_5
_w4_row_1_6
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_1_6
        move.b d5,(1152,a0)
.transparent_w4_row_1_6
_w4_row_1_7
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_1_7
        move.b d5,(1344,a0)
.transparent_w4_row_1_7
        lea (1536,a0),a0
        move.w d2,a1
        suba.w #8,a1
        move.w a1,d2
        cmp.w #7,d2
        bge _w4_chunk_1
        tst.w d2
        bmi _w4_done_1
_w4_tail_1
_w4_row_1_8
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_1_8
        move.b d5,(a0)
.transparent_w4_row_1_8
        lea (192,a0),a0
        dbf d2,_w4_tail_1
_w4_done_1
        move.l (sp)+,a1
        tst.b d5
        bra _w4_resume_1
_w4_resume_1 dc.w $4ef9
        dc.l 0

_w4_entry_2
        move.l a1,-(sp)
        cmp.w #7,d2
        bge _w4_chunk_2
        bra _w4_tail_2
_w4_chunk_2
_w4_row_2_0
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_2_0
        move.b d5,(a0)
.transparent_w4_row_2_0
_w4_row_2_1
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_2_1
        move.b d5,(192,a0)
.transparent_w4_row_2_1
_w4_row_2_2
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_2_2
        move.b d5,(384,a0)
.transparent_w4_row_2_2
_w4_row_2_3
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_2_3
        move.b d5,(576,a0)
.transparent_w4_row_2_3
_w4_row_2_4
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_2_4
        move.b d5,(768,a0)
.transparent_w4_row_2_4
_w4_row_2_5
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_2_5
        move.b d5,(960,a0)
.transparent_w4_row_2_5
_w4_row_2_6
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_2_6
        move.b d5,(1152,a0)
.transparent_w4_row_2_6
_w4_row_2_7
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_2_7
        move.b d5,(1344,a0)
.transparent_w4_row_2_7
        lea (1536,a0),a0
        move.w d2,a1
        suba.w #8,a1
        move.w a1,d2
        cmp.w #7,d2
        bge _w4_chunk_2
        tst.w d2
        bmi _w4_done_2
_w4_tail_2
_w4_row_2_8
        move.w (a5)+,d0
        move.b (a3,d0.w),d5
        move.b (a2,d5.w),d5
        beq .transparent_w4_row_2_8
        move.b d5,(a0)
.transparent_w4_row_2_8
        lea (192,a0),a0
        dbf d2,_w4_tail_2
_w4_done_2
        move.l (sp)+,a1
        tst.b d5
        bra _w4_resume_2
_w4_resume_2 dc.w $4ef9
        dc.l 0
        IFD VERIFY
        INCLUDE sprites_verify.s
        ENDC
