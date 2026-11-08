; W5: exact memoization of all eight two-DIVU ray quotients.
; Full divisor tags prevent collisions; guarded continuations discard D7/CCR.
; No approximate arithmetic or change to the once-per-view heading division.
; Select the cache on 68000/10; 68020+ keep their faster original DIVU pair.
_w5_install
        movem.l d0-a6,-(sp)
        move.l (_custom2,pc),d0
        btst #4,d0
        beq .done
        move.l (_lov_attnflags,pc),d0
        btst #1,d0              ; AFB_68020
        beq .cpu_ok
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #6,d0              ; reciprocal twin may exercise either CPU
        bne .cpu_ok
        ENDC
        bra .done
.cpu_ok
        move.l (_custom1,pc),d0
        tst.l d0
        bne .done
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #6,d0
        beq .no_units
        bsr _w5_unit_test
.no_units
        ENDC
        move.l (_h12,pc),a0
        bsr _w5_check_liveness
        cmp.l #$2e3c0001,(h12_02998,a0)
        bne .bad
        cmp.l #$00008ec2,(h12_0299c,a0)
        bne .bad
        cmp.l #$2e3c0001,(h12_02de4,a0)
        bne .bad
        cmp.l #$00008ec3,(h12_02de8,a0)
        bne .bad
        cmp.l #$2e3c0001,(h12_03236,a0)
        bne .bad
        cmp.l #$00008ec3,(h12_0323a,a0)
        bne .bad
        cmp.l #$2e3c0001,(h12_03676,a0)
        bne .bad
        cmp.l #$00008ec2,(h12_0367a,a0)
        bne .bad
        cmp.l #$2e3c0001,(h12_03ab4,a0)
        bne .bad
        cmp.l #$00008ec2,(h12_03ab8,a0)
        bne .bad
        cmp.l #$2e3c0001,(h12_03f0c,a0)
        bne .bad
        cmp.l #$00008ec3,(h12_03f10,a0)
        bne .bad
        cmp.l #$2e3c0001,(h12_0435e,a0)
        bne .bad
        cmp.l #$00008ec3,(h12_04362,a0)
        bne .bad
        cmp.l #$2e3c0001,(h12_0479c,a0)
        bne .bad
        cmp.l #$00008ec2,(h12_047a0,a0)
        bne .bad
        lea (_w5_resume_0+2,pc),a1
        lea (h12_029aa,a0),a2
        move.l a2,(a1)
        ; PERF_RANGE h12:02998 6 bit=4
        move.w #$4ef9,(h12_02998,a0)
        lea (_w5_entry_0,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #6,d0
        beq .normal0
        lea (_w5_twin_entry_0,pc),a1
.normal0
        ENDC
        move.l a1,(h12_0299a,a0)
        lea (_w5_resume_1+2,pc),a1
        lea (h12_02df6,a0),a2
        move.l a2,(a1)
        ; PERF_RANGE h12:02de4 6 bit=4
        move.w #$4ef9,(h12_02de4,a0)
        lea (_w5_entry_1,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #6,d0
        beq .normal1
        lea (_w5_twin_entry_1,pc),a1
.normal1
        ENDC
        move.l a1,(h12_02de6,a0)
        lea (_w5_resume_2+2,pc),a1
        lea (h12_03248,a0),a2
        move.l a2,(a1)
        ; PERF_RANGE h12:03236 6 bit=4
        move.w #$4ef9,(h12_03236,a0)
        lea (_w5_entry_2,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #6,d0
        beq .normal2
        lea (_w5_twin_entry_2,pc),a1
.normal2
        ENDC
        move.l a1,(h12_03238,a0)
        lea (_w5_resume_3+2,pc),a1
        lea (h12_03688,a0),a2
        move.l a2,(a1)
        ; PERF_RANGE h12:03676 6 bit=4
        move.w #$4ef9,(h12_03676,a0)
        lea (_w5_entry_3,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #6,d0
        beq .normal3
        lea (_w5_twin_entry_3,pc),a1
.normal3
        ENDC
        move.l a1,(h12_03678,a0)
        lea (_w5_resume_4+2,pc),a1
        lea (h12_03ac6,a0),a2
        move.l a2,(a1)
        ; PERF_RANGE h12:03ab4 6 bit=4
        move.w #$4ef9,(h12_03ab4,a0)
        lea (_w5_entry_4,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #6,d0
        beq .normal4
        lea (_w5_twin_entry_4,pc),a1
.normal4
        ENDC
        move.l a1,(h12_03ab6,a0)
        lea (_w5_resume_5+2,pc),a1
        lea (h12_03f1e,a0),a2
        move.l a2,(a1)
        ; PERF_RANGE h12:03f0c 6 bit=4
        move.w #$4ef9,(h12_03f0c,a0)
        lea (_w5_entry_5,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #6,d0
        beq .normal5
        lea (_w5_twin_entry_5,pc),a1
.normal5
        ENDC
        move.l a1,(h12_03f0e,a0)
        lea (_w5_resume_6+2,pc),a1
        lea (h12_04370,a0),a2
        move.l a2,(a1)
        ; PERF_RANGE h12:0435e 6 bit=4
        move.w #$4ef9,(h12_0435e,a0)
        lea (_w5_entry_6,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #6,d0
        beq .normal6
        lea (_w5_twin_entry_6,pc),a1
.normal6
        ENDC
        move.l a1,(h12_04360,a0)
        lea (_w5_resume_7+2,pc),a1
        lea (h12_047ae,a0),a2
        move.l a2,(a1)
        ; PERF_RANGE h12:0479c 6 bit=4
        move.w #$4ef9,(h12_0479c,a0)
        lea (_w5_entry_7,pc),a1
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #6,d0
        beq .normal7
        lea (_w5_twin_entry_7,pc),a1
.normal7
        ENDC
        move.l a1,(h12_0479e,a0)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
.done   movem.l (sp)+,d0-a6
        rts
.bad    lea (_w5_badcode,pc),a0
        bra _c2p_abort
_w5_badcode dc.b "W5: unexpected ray reciprocal setup",0
        EVEN
; Fail closed if any continuation starts reading the discarded D7/CCR state.
; Recognize its coordinate load and exact sequence through the first ADD.
_w5_check_liveness
        lea (_w5_tail_offsets,pc),a1
        moveq #7,d0
.loop   move.l a0,a3
        adda.w (a1)+,a3
        move.w (a3)+,d1
        move.w d1,d3
        and.w #$fdff,d1
        cmp.w #$303a,d1
        bne _w5_bad_tail
        and.w #$0200,d3
        lsr.w #8,d3
        lsr.w #1,d3             ; coordinate D0 or D1
        moveq #3,d4
        sub.w d3,d4             ; quotient D3 or D2
        move.l a3,-(sp)
        move.l a0,a3
        adda.w (-2,a1),a3
        suba.w #12,a3          ; complete skipped DIVU construction
        move.w d3,d5
        addq.w #2,d5           ; divisor D2 or D3
        move.w #$8ec0,d1
        or.w d5,d1
        bsr _w5_expect_tail
        move.w d4,d5
        lsl.w #8,d5
        lsl.w #1,d5            ; quotient opcode register field
        move.w #$2007,d1
        or.w d5,d1
        bsr _w5_expect_tail
        move.w #$4840,d1
        or.w d4,d1
        bsr _w5_expect_tail
        move.w #$4247,d1
        bsr _w5_expect_tail
        move.w #$8ec2,d1
        or.w d3,d1
        bsr _w5_expect_tail
        move.w #$3007,d1
        or.w d5,d1
        bsr _w5_expect_tail
        move.l (sp)+,a3
        move.l a3,a4            ; PC-relative displacement word
        adda.w (a3)+,a4
        lea (h12_00008,a0),a2   ; coordinate D0 (D1 is 2 bytes before)
        tst.w d3
        beq .source
        subq.l #2,a2
.source cmpa.l a2,a4
        bne _w5_bad_tail
        move.w #$4640,d1        ; optional NOT of the coordinate
        or.w d3,d1
        cmp.w (a3),d1
        bne .body
        addq.l #2,a3
.body   move.w #$3e00,d1        ; MOVE.W coordinate,D7
        or.w d3,d1
        bsr _w5_expect_tail
        move.w #$4840,d1        ; SWAP quotient
        or.w d4,d1
        bsr _w5_expect_tail
        move.w #$cec0,d1        ; MULU.W quotient,D7 (old high word unused)
        or.w d4,d1
        bsr _w5_expect_tail
        move.w #$4840,d1
        or.w d4,d1
        bsr _w5_expect_tail
        move.w d3,d5
        lsl.w #8,d5
        lsl.w #1,d5
        move.w #$c0c0,d1        ; MULU.W quotient,coordinate
        or.w d4,d1
        or.w d5,d1
        bsr _w5_expect_tail
        move.w #$4240,d1        ; CLR.W coordinate
        or.w d3,d1
        bsr _w5_expect_tail
        move.w #$4840,d1        ; SWAP coordinate
        or.w d3,d1
        bsr _w5_expect_tail
        move.w #$d087,d1        ; ADD.L D7,coordinate (defines all five flags)
        or.w d5,d1
        bsr _w5_expect_tail
        dbf d0,.loop
        rts
_w5_expect_tail
        cmp.w (a3)+,d1
        bne _w5_bad_tail
        rts
_w5_bad_tail
        lea (_w5_tail_badmsg,pc),a0
        bra _c2p_abort
_w5_tail_badmsg dc.b "W5: unexpected ray continuation liveness",0
        EVEN
_w5_tail_offsets dc.w h12_029aa,h12_02df6,h12_03248,h12_03688,h12_03ac6,h12_03f1e,h12_04370,h12_047ae

_w5_entry_0
        exg d2,d3
        bsr _w5_reciprocal
        exg d2,d3
_w5_resume_0 dc.w $4ef9
        dc.l 0
_w5_entry_1
        bsr _w5_reciprocal
_w5_resume_1 dc.w $4ef9
        dc.l 0
_w5_entry_2
        bsr _w5_reciprocal
_w5_resume_2 dc.w $4ef9
        dc.l 0
_w5_entry_3
        exg d2,d3
        bsr _w5_reciprocal
        exg d2,d3
_w5_resume_3 dc.w $4ef9
        dc.l 0
_w5_entry_4
        exg d2,d3
        bsr _w5_reciprocal
        exg d2,d3
_w5_resume_4 dc.w $4ef9
        dc.l 0
_w5_entry_5
        bsr _w5_reciprocal
_w5_resume_5 dc.w $4ef9
        dc.l 0
_w5_entry_6
        bsr _w5_reciprocal
_w5_resume_6 dc.w $4ef9
        dc.l 0
_w5_entry_7
        exg d2,d3
        bsr _w5_reciprocal
        exg d2,d3
_w5_resume_7 dc.w $4ef9
        dc.l 0
_w5_reciprocal
        move.l a0,-(sp)
        move.w d3,d7
        beq .zero
        ; D7 and CCR are dead before the unchanged continuation's first ADD.
        ; Every site overwrites D7 with a word then MULU, and reads no old flags.
        ; VERIFY compares the complete state after that mathematical continuation.
        and.w #1023,d7
        lsl.w #3,d7
        lea (_w5_keys,pc),a0
        cmp.w (4,a0,d7.w),d3
        bne .miss
_w5_cache_hit EQU *
        move.l (a0,d7.w),d2
        bra .result
.miss
_w5_cache_miss EQU *
        lea (a0,d7.w),a0
        bsr .original
        move.l d2,(a0)
        move.w d3,(4,a0)
.result
        move.l (sp)+,a0
        rts
.zero
        move.l (sp)+,a0
.original
_w5_original
        move.l #$10000,d7
        divu.w d3,d7
        move.l d7,d2
        swap d2
        clr.w d7
        divu.w d3,d7
        move.w d7,d2
        rts
        IFD VERIFY
_w5_twin_entry_0
        bsr _w5_twin_swapped
        bra _w5_resume_0
_w5_twin_entry_1
        bsr _w5_twin
        bra _w5_resume_1
_w5_twin_entry_2
        bsr _w5_twin
        bra _w5_resume_2
_w5_twin_entry_3
        bsr _w5_twin_swapped
        bra _w5_resume_3
_w5_twin_entry_4
        bsr _w5_twin_swapped
        bra _w5_resume_4
_w5_twin_entry_5
        bsr _w5_twin
        bra _w5_resume_5
_w5_twin_entry_6
        bsr _w5_twin
        bra _w5_resume_6
_w5_twin_entry_7
        bsr _w5_twin_swapped
        bra _w5_resume_7
_w5_twin_swapped
        exg d2,d3
        bsr _w5_twin
        exg d2,d3
        rts
_w5_twin
        movem.l d0-a6,-(sp)
_verify_sr_15 EQU *
        move.w sr,-(sp)
        bsr _w5_reciprocal
        movem.l d0-a6,-(sp)
_verify_sr_16 EQU *
        move.w sr,-(sp)
        bsr _w5_followup
        movem.l d0-a6,-(sp)
_verify_sr_13 EQU *
        move.w sr,-(sp)
        pea .expected_done(pc)
        pea (_w5_expected,pc)
        move.w (132,sp),ccr
        movem.l (134,sp),d0-a6
        rts
.expected_done
        movem.l d0-a6,-(sp)
_verify_sr_14 EQU *
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
        lea (_w5_tests,pc),a0
        addq.l #1,(a0)
        move.w (124,sp),ccr
        movem.l (126,sp),d0-a6
        lea (248,sp),sp
        rts
.different lea (_w5_diffmsg,pc),a0
        bra _c2p_abort
; Canonical form of every site's unchanged continuation through its first ADD.
; Coordinate register selection and optional NOT differ, but D7/flags liveness
; and this reciprocal-times-coordinate operation are the same at all eight sites.
_w5_expected
        bsr _w5_original
_w5_followup
        move.w d0,d7
        swap d2
        mulu.w d2,d7
        swap d2
        mulu.w d2,d0
        clr.w d0
        swap d0
        add.l d7,d0
        rts
_w5_diffmsg dc.b "W5 twin: differing ray result or post-continuation state",0
        EVEN
_w5_tests dc.l 0
_w5_units dc.l 0
_w5_unit_test
        moveq #1,d3
.divisor
        moveq #0,d0
        andi #$ef,ccr
        bsr _w5_twin
        moveq #-1,d0
        ori #$10,ccr
        bsr _w5_twin
        ; Test the D2-divisor/D3-result wrappers with the same full range.
        move.l d3,-(sp)
        move.w d3,d2
        move.w d3,d0
        andi #$ef,ccr
        bsr _w5_twin_swapped
        move.w #$8000,d0
        ori #$10,ccr
        bsr _w5_twin_swapped
        move.l (sp)+,d3
        addq.w #1,d3
        bne .divisor
        lea (_w5_tests,pc),a0
        move.l (a0),(_w5_units-_w5_tests,a0)
        clr.l (a0)
        ; Restore the cold-cache state for live rendering.
        lea (_w5_keys,pc),a0
        move.w #1024*8/4-1,d0
.cold   clr.l (a0)+
        dbf d0,.cold
        rts
        ENDC
        CNOP 0,4
; Exact Q32, complete divisor16, two unused alignment bytes per record.
_w5_keys ds.b 1024*8
