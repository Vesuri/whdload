        IFD VERIFY
        IFD FLAT_TEST
        IFEQ FLAT_PITCH
        FAIL "FLAT_TEST requires FLAT_PITCH=1"
        ENDC
s60_flat_results:
        IFNE MOVE_ZERO
        dc.b 'F762' ; 80 zero-speed cases call the wrapper-only shortcut
        ELSE
        dc.b 'F761'
        ENDC
        dc.w 0,0 ; completed cases, actor mismatches
s60_flat_seed: ds.b $6e
s60_flat_expected: ds.b $6e
s60_flat_actual: ds.b $6e
s60_flat_yaws:
        dc.w $8000,$8001,$bfff,$c000,$c001,-17,-16,-1
        dc.w 0,1,15,16,$3fff,$4000,$4001,$7fff
s60_flat_speeds: dc.w $8000,$8001,-1,0,1,$7fff
s60_flat_select:
        movem.l d0-d1/a0-a2,-(sp)
        move.l (s60_code,pc),a0
        adda.l #$86ae,a0
        move.w d0,(a0)
        IFNE MOVE_WORD_MUL
        move.l (s60_code,pc),a0
        adda.l #$8000,a0
        cmp.w #$8240,d0
        bne .fast_multiply
        move.l #$4eba733e,($06cc,a0)
        move.l #$4eba72f8,($0712,a0)
        move.l #$4eba72b0,($075a,a0)
        move.l #$4eba7284,($0786,a0)
        move.l #$4eba725e,($07ac,a0)
        bra .multiply_ready
.fast_multiply:
        move.l #$c1c14e71,($06cc,a0)
        move.l #$c1c14e71,($0712,a0)
        move.l #$c1c14e71,($075a,a0)
        move.l #$c1c14e71,($0786,a0)
        move.l #$c1c14e71,($07ac,a0)
.multiply_ready:
        ENDC
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d1/a0-a2
        rts
s60_test_flat:
        move.l (s60_ticks,pc),d0
        cmp.l #FLAT_TEST,d0
        bne .done
        move.w (s60_flat_results+4,pc),d0
        bne .done
        movem.l d2-d7/a2-a6,-(sp)
        moveq #0,d4
.case:  lea (s60_flat_seed,pc),a2
        move.l a2,a0
        moveq #$6e/2-1,d0
.clear: clr.w (a0)+
        dbf d0,.clear
        move.l #$7ffffff0,(8,a2)
        move.l #$80000010,(12,a2)
        move.l #$7ffff000,(16,a2)
        move.w #$7fff,(58,a2)
        move.w #$8000,(60,a2)
        move.w #-1,(62,a2)
        move.w d4,d0
        and.w #15,d0
        add.w d0,d0
        lea (s60_flat_yaws,pc),a0
        move.w (a0,d0.w),(24,a2)
        moveq #0,d0
        move.w d4,d0
        lsr.w #4,d0
        divu #6,d0
        move.w d0,d7 ; variant 0..4
        swap d0
        add.w d0,d0
        lea (s60_flat_speeds,pc),a0
        move.w (a0,d0.w),(64,a2)
        tst.w d7
        beq .ready ; native flat control, bank zero
        move.w #$8000,(22,a2)
        cmp.w #1,d7
        beq .ready ; exact cardinal/boundary yaws with bank nonzero
        move.w #$1234,(56,a2) ; other variants advance/wrap yaw first
        cmp.w #2,d7
        bne .nonzero
        move.w #-1,(20,a2)
        move.w #1,(52,a2) ; pitch becomes exactly zero
        move.w #$7fff,(22,a2)
        move.w #1,(54,a2) ; bank wraps negative
        bra .ready
.nonzero:
        cmp.w #4,d7
        bne .small_pitch
        move.w #$8000,(20,a2) ; cos=-16384 with MIN speed gives +32768
        bra .ready ; preserve the two subsequent wide products at this boundary
.small_pitch:
        move.w #1,(52,a2) ; pitch becomes nonzero: retain the general path
.ready:
        move.l a2,a0
        lea (s60_flat_expected,pc),a1
        lea (s60_flat_actual,pc),a3
        moveq #$6e/2-1,d0
.copy:  move.w (a0)+,d1
        move.w d1,(a1)+
        move.w d1,(a3)+
        dbf d0,.copy
        move.w #$8240,d0
        bsr s60_flat_select
        pea (s60_flat_expected,pc)
        bsr s60_move_native
        addq.l #4,sp
        move.w #$4a40,d0
        bsr s60_flat_select
        IFNE MOVE_ZERO
        lea (s60_flat_actual,pc),a3
        tst.w (64,a3)
        bne .native_actual
        bsr s60_move_zero
        bra .actual_done
.native_actual:
        ENDC
        pea (s60_flat_actual,pc)
        bsr s60_move_native
        addq.l #4,sp
.actual_done:
        lea (s60_flat_expected,pc),a0
        lea (s60_flat_actual,pc),a1
        moveq #$6e/2-1,d0
.compare:
        cmpm.w (a0)+,(a1)+
        bne .error
        dbf d0,.compare
        bra .next
.error: lea (s60_flat_results,pc),a0
        addq.w #1,(6,a0)
.next:  lea (s60_flat_results,pc),a0
        addq.w #1,(4,a0)
        addq.w #1,d4
        cmp.w #480,d4
        bne .case
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
