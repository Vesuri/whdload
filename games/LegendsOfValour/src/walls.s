; W3: unroll 16 paired wall pixels with fixed destination displacements.
; Keep NOT, ADD/ADDX, CMP and DBGE exactly; advance pointers at each exit.
; The larger unroll benefits 68000/10; 68020+ retain the original loop.
_w3_install
        movem.l d0-a6,-(sp)
        move.l (_custom2,pc),d0
        btst #2,d0
        beq .done
        move.l (_lov_attnflags,pc),d0
        btst #1,d0              ; AFB_68020
        beq .cpu_ok
        IFD VERIFY
        ; Allow the pixel twin to exercise these bodies on either CPU. Ordinary
        ; captures and shipping builds keep the original 68020+ loop untouched.
        move.l (_custom5,pc),d0
        btst #4,d0
        bne .cpu_ok
        ENDC
        bra .done
.cpu_ok
        move.l (_custom1,pc),d0
        tst.l d0
        bne .done
        move.l (_h12,pc),a0
        cmp.l #$b8435cca,($4c50,a0)
        bne .bad
        cmp.w #$ffe4,($4c54,a0)
        bne .bad
        cmp.l #$b8435cca,($4cf4,a0)
        bne .bad
        cmp.w #$ffe4,($4cf8,a0)
        bne .bad
        cmp.l #$b8435cca,($4d78,a0)
        bne .bad
        cmp.w #$ffe4,($4d7c,a0)
        bne .bad
        IFD VERIFY
        bsr _w3_verify_install
        ENDC
        lea (_w3_resume_0+2,pc),a1
        lea ($4c56,a0),a2
        move.l a2,(a1)
        ; PERF_RANGE h12:04c50 6 bit=2
        move.w #$4ef9,($4c50,a0)
        lea (_w3_entry_0,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #4,d0
        beq .normal0
        lea (_w3_twin_return,pc),a2
        lea (_w3_resume_0+2,pc),a3
        move.l a2,(a3)
        lea (_w3_twin_0,pc),a1
.normal0
        ENDC
        move.l a1,($4c52,a0)
        lea (_w3_resume_1+2,pc),a1
        lea ($4cfa,a0),a2
        move.l a2,(a1)
        ; PERF_RANGE h12:04cf4 6 bit=2
        move.w #$4ef9,($4cf4,a0)
        lea (_w3_entry_1,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #4,d0
        beq .normal1
        lea (_w3_twin_return,pc),a2
        lea (_w3_resume_1+2,pc),a3
        move.l a2,(a3)
        lea (_w3_twin_1,pc),a1
.normal1
        ENDC
        move.l a1,($4cf6,a0)
        lea (_w3_resume_2+2,pc),a1
        lea ($4d7e,a0),a2
        move.l a2,(a1)
        ; PERF_RANGE h12:04d78 6 bit=2
        move.w #$4ef9,($4d78,a0)
        lea (_w3_entry_2,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #4,d0
        beq .normal2
        lea (_w3_twin_return,pc),a2
        lea (_w3_resume_2+2,pc),a3
        move.l a2,(a3)
        lea (_w3_twin_2,pc),a1
.normal2
        ENDC
        move.l a1,($4d7a,a0)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
.done   movem.l (sp)+,d0-a6
        rts
.bad    lea (_w3_badcode,pc),a0
        bra _c2p_abort
_w3_badcode dc.b "W3: unexpected wall-column loop",0
        EVEN

_w3_entry_0
        cmp.w d3,d4
        dbge d2,_w3_pair_0_0
        bra _w3_resume_0
_w3_pair_0_0
        not.w d4
        move.b (a6,d4.w),(a1)
        not.w d4
        move.b (a6,d4.w),(a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_1
        lea (-192,a1),a1
        lea (192,a2),a2
        bra _w3_resume_0
_w3_pair_0_1
        not.w d4
        move.b (a6,d4.w),(-192,a1)
        not.w d4
        move.b (a6,d4.w),(192,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_2
        lea (-384,a1),a1
        lea (384,a2),a2
        bra _w3_resume_0
_w3_pair_0_2
        not.w d4
        move.b (a6,d4.w),(-384,a1)
        not.w d4
        move.b (a6,d4.w),(384,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_3
        lea (-576,a1),a1
        lea (576,a2),a2
        bra _w3_resume_0
_w3_pair_0_3
        not.w d4
        move.b (a6,d4.w),(-576,a1)
        not.w d4
        move.b (a6,d4.w),(576,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_4
        lea (-768,a1),a1
        lea (768,a2),a2
        bra _w3_resume_0
_w3_pair_0_4
        not.w d4
        move.b (a6,d4.w),(-768,a1)
        not.w d4
        move.b (a6,d4.w),(768,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_5
        lea (-960,a1),a1
        lea (960,a2),a2
        bra _w3_resume_0
_w3_pair_0_5
        not.w d4
        move.b (a6,d4.w),(-960,a1)
        not.w d4
        move.b (a6,d4.w),(960,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_6
        lea (-1152,a1),a1
        lea (1152,a2),a2
        bra _w3_resume_0
_w3_pair_0_6
        not.w d4
        move.b (a6,d4.w),(-1152,a1)
        not.w d4
        move.b (a6,d4.w),(1152,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_7
        lea (-1344,a1),a1
        lea (1344,a2),a2
        bra _w3_resume_0
_w3_pair_0_7
        not.w d4
        move.b (a6,d4.w),(-1344,a1)
        not.w d4
        move.b (a6,d4.w),(1344,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_8
        lea (-1536,a1),a1
        lea (1536,a2),a2
        bra _w3_resume_0
_w3_pair_0_8
        not.w d4
        move.b (a6,d4.w),(-1536,a1)
        not.w d4
        move.b (a6,d4.w),(1536,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_9
        lea (-1728,a1),a1
        lea (1728,a2),a2
        bra _w3_resume_0
_w3_pair_0_9
        not.w d4
        move.b (a6,d4.w),(-1728,a1)
        not.w d4
        move.b (a6,d4.w),(1728,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_10
        lea (-1920,a1),a1
        lea (1920,a2),a2
        bra _w3_resume_0
_w3_pair_0_10
        not.w d4
        move.b (a6,d4.w),(-1920,a1)
        not.w d4
        move.b (a6,d4.w),(1920,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_11
        lea (-2112,a1),a1
        lea (2112,a2),a2
        bra _w3_resume_0
_w3_pair_0_11
        not.w d4
        move.b (a6,d4.w),(-2112,a1)
        not.w d4
        move.b (a6,d4.w),(2112,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_12
        lea (-2304,a1),a1
        lea (2304,a2),a2
        bra _w3_resume_0
_w3_pair_0_12
        not.w d4
        move.b (a6,d4.w),(-2304,a1)
        not.w d4
        move.b (a6,d4.w),(2304,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_13
        lea (-2496,a1),a1
        lea (2496,a2),a2
        bra _w3_resume_0
_w3_pair_0_13
        not.w d4
        move.b (a6,d4.w),(-2496,a1)
        not.w d4
        move.b (a6,d4.w),(2496,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_14
        lea (-2688,a1),a1
        lea (2688,a2),a2
        bra _w3_resume_0
_w3_pair_0_14
        not.w d4
        move.b (a6,d4.w),(-2688,a1)
        not.w d4
        move.b (a6,d4.w),(2688,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_15
        lea (-2880,a1),a1
        lea (2880,a2),a2
        bra _w3_resume_0
_w3_pair_0_15
        not.w d4
        move.b (a6,d4.w),(-2880,a1)
        not.w d4
        move.b (a6,d4.w),(2880,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_0_16
        lea (-3072,a1),a1
        lea (3072,a2),a2
        bra _w3_resume_0
_w3_pair_0_16
        lea (-3072,a1),a1
        lea (3072,a2),a2
        bra _w3_pair_0_0
_w3_resume_0 dc.w $4ef9
        dc.l 0

_w3_entry_1
        cmp.w d3,d4
        dbge d2,_w3_pair_1_0
        bra _w3_resume_1
_w3_pair_1_0
        not.w d4
        move.b (a6,d4.w),(a1)
        not.w d4
        move.b (a6,d4.w),(a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_1
        lea (-192,a1),a1
        lea (192,a2),a2
        bra _w3_resume_1
_w3_pair_1_1
        not.w d4
        move.b (a6,d4.w),(-192,a1)
        not.w d4
        move.b (a6,d4.w),(192,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_2
        lea (-384,a1),a1
        lea (384,a2),a2
        bra _w3_resume_1
_w3_pair_1_2
        not.w d4
        move.b (a6,d4.w),(-384,a1)
        not.w d4
        move.b (a6,d4.w),(384,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_3
        lea (-576,a1),a1
        lea (576,a2),a2
        bra _w3_resume_1
_w3_pair_1_3
        not.w d4
        move.b (a6,d4.w),(-576,a1)
        not.w d4
        move.b (a6,d4.w),(576,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_4
        lea (-768,a1),a1
        lea (768,a2),a2
        bra _w3_resume_1
_w3_pair_1_4
        not.w d4
        move.b (a6,d4.w),(-768,a1)
        not.w d4
        move.b (a6,d4.w),(768,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_5
        lea (-960,a1),a1
        lea (960,a2),a2
        bra _w3_resume_1
_w3_pair_1_5
        not.w d4
        move.b (a6,d4.w),(-960,a1)
        not.w d4
        move.b (a6,d4.w),(960,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_6
        lea (-1152,a1),a1
        lea (1152,a2),a2
        bra _w3_resume_1
_w3_pair_1_6
        not.w d4
        move.b (a6,d4.w),(-1152,a1)
        not.w d4
        move.b (a6,d4.w),(1152,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_7
        lea (-1344,a1),a1
        lea (1344,a2),a2
        bra _w3_resume_1
_w3_pair_1_7
        not.w d4
        move.b (a6,d4.w),(-1344,a1)
        not.w d4
        move.b (a6,d4.w),(1344,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_8
        lea (-1536,a1),a1
        lea (1536,a2),a2
        bra _w3_resume_1
_w3_pair_1_8
        not.w d4
        move.b (a6,d4.w),(-1536,a1)
        not.w d4
        move.b (a6,d4.w),(1536,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_9
        lea (-1728,a1),a1
        lea (1728,a2),a2
        bra _w3_resume_1
_w3_pair_1_9
        not.w d4
        move.b (a6,d4.w),(-1728,a1)
        not.w d4
        move.b (a6,d4.w),(1728,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_10
        lea (-1920,a1),a1
        lea (1920,a2),a2
        bra _w3_resume_1
_w3_pair_1_10
        not.w d4
        move.b (a6,d4.w),(-1920,a1)
        not.w d4
        move.b (a6,d4.w),(1920,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_11
        lea (-2112,a1),a1
        lea (2112,a2),a2
        bra _w3_resume_1
_w3_pair_1_11
        not.w d4
        move.b (a6,d4.w),(-2112,a1)
        not.w d4
        move.b (a6,d4.w),(2112,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_12
        lea (-2304,a1),a1
        lea (2304,a2),a2
        bra _w3_resume_1
_w3_pair_1_12
        not.w d4
        move.b (a6,d4.w),(-2304,a1)
        not.w d4
        move.b (a6,d4.w),(2304,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_13
        lea (-2496,a1),a1
        lea (2496,a2),a2
        bra _w3_resume_1
_w3_pair_1_13
        not.w d4
        move.b (a6,d4.w),(-2496,a1)
        not.w d4
        move.b (a6,d4.w),(2496,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_14
        lea (-2688,a1),a1
        lea (2688,a2),a2
        bra _w3_resume_1
_w3_pair_1_14
        not.w d4
        move.b (a6,d4.w),(-2688,a1)
        not.w d4
        move.b (a6,d4.w),(2688,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_15
        lea (-2880,a1),a1
        lea (2880,a2),a2
        bra _w3_resume_1
_w3_pair_1_15
        not.w d4
        move.b (a6,d4.w),(-2880,a1)
        not.w d4
        move.b (a6,d4.w),(2880,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_1_16
        lea (-3072,a1),a1
        lea (3072,a2),a2
        bra _w3_resume_1
_w3_pair_1_16
        lea (-3072,a1),a1
        lea (3072,a2),a2
        bra _w3_pair_1_0
_w3_resume_1 dc.w $4ef9
        dc.l 0

_w3_entry_2
        cmp.w d3,d4
        dbge d2,_w3_pair_2_0
        bra _w3_resume_2
_w3_pair_2_0
        not.w d4
        move.b (a6,d4.w),(a1)
        not.w d4
        move.b (a6,d4.w),(a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_1
        lea (-192,a1),a1
        lea (192,a2),a2
        bra _w3_resume_2
_w3_pair_2_1
        not.w d4
        move.b (a6,d4.w),(-192,a1)
        not.w d4
        move.b (a6,d4.w),(192,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_2
        lea (-384,a1),a1
        lea (384,a2),a2
        bra _w3_resume_2
_w3_pair_2_2
        not.w d4
        move.b (a6,d4.w),(-384,a1)
        not.w d4
        move.b (a6,d4.w),(384,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_3
        lea (-576,a1),a1
        lea (576,a2),a2
        bra _w3_resume_2
_w3_pair_2_3
        not.w d4
        move.b (a6,d4.w),(-576,a1)
        not.w d4
        move.b (a6,d4.w),(576,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_4
        lea (-768,a1),a1
        lea (768,a2),a2
        bra _w3_resume_2
_w3_pair_2_4
        not.w d4
        move.b (a6,d4.w),(-768,a1)
        not.w d4
        move.b (a6,d4.w),(768,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_5
        lea (-960,a1),a1
        lea (960,a2),a2
        bra _w3_resume_2
_w3_pair_2_5
        not.w d4
        move.b (a6,d4.w),(-960,a1)
        not.w d4
        move.b (a6,d4.w),(960,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_6
        lea (-1152,a1),a1
        lea (1152,a2),a2
        bra _w3_resume_2
_w3_pair_2_6
        not.w d4
        move.b (a6,d4.w),(-1152,a1)
        not.w d4
        move.b (a6,d4.w),(1152,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_7
        lea (-1344,a1),a1
        lea (1344,a2),a2
        bra _w3_resume_2
_w3_pair_2_7
        not.w d4
        move.b (a6,d4.w),(-1344,a1)
        not.w d4
        move.b (a6,d4.w),(1344,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_8
        lea (-1536,a1),a1
        lea (1536,a2),a2
        bra _w3_resume_2
_w3_pair_2_8
        not.w d4
        move.b (a6,d4.w),(-1536,a1)
        not.w d4
        move.b (a6,d4.w),(1536,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_9
        lea (-1728,a1),a1
        lea (1728,a2),a2
        bra _w3_resume_2
_w3_pair_2_9
        not.w d4
        move.b (a6,d4.w),(-1728,a1)
        not.w d4
        move.b (a6,d4.w),(1728,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_10
        lea (-1920,a1),a1
        lea (1920,a2),a2
        bra _w3_resume_2
_w3_pair_2_10
        not.w d4
        move.b (a6,d4.w),(-1920,a1)
        not.w d4
        move.b (a6,d4.w),(1920,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_11
        lea (-2112,a1),a1
        lea (2112,a2),a2
        bra _w3_resume_2
_w3_pair_2_11
        not.w d4
        move.b (a6,d4.w),(-2112,a1)
        not.w d4
        move.b (a6,d4.w),(2112,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_12
        lea (-2304,a1),a1
        lea (2304,a2),a2
        bra _w3_resume_2
_w3_pair_2_12
        not.w d4
        move.b (a6,d4.w),(-2304,a1)
        not.w d4
        move.b (a6,d4.w),(2304,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_13
        lea (-2496,a1),a1
        lea (2496,a2),a2
        bra _w3_resume_2
_w3_pair_2_13
        not.w d4
        move.b (a6,d4.w),(-2496,a1)
        not.w d4
        move.b (a6,d4.w),(2496,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_14
        lea (-2688,a1),a1
        lea (2688,a2),a2
        bra _w3_resume_2
_w3_pair_2_14
        not.w d4
        move.b (a6,d4.w),(-2688,a1)
        not.w d4
        move.b (a6,d4.w),(2688,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_15
        lea (-2880,a1),a1
        lea (2880,a2),a2
        bra _w3_resume_2
_w3_pair_2_15
        not.w d4
        move.b (a6,d4.w),(-2880,a1)
        not.w d4
        move.b (a6,d4.w),(2880,a2)
        add.w d7,d6
        addx.w d5,d4
        cmp.w d3,d4
        dbge d2,_w3_pair_2_16
        lea (-3072,a1),a1
        lea (3072,a2),a2
        bra _w3_resume_2
_w3_pair_2_16
        lea (-3072,a1),a1
        lea (3072,a2),a2
        bra _w3_pair_2_0
_w3_resume_2 dc.w $4ef9
        dc.l 0
        IFD VERIFY
        INCLUDE walls_verify.s
        ENDC
