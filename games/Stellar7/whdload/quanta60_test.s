        IFD VERIFY
        IFD QUANTA_TEST
; Compare all native input bytes with the preceding table-loop implementation.
; Restore full native constants before the candidate to catch omitted stores.
S60_QUANTA_START = $fea8
S60_QUANTA_BYTES = $100d6-S60_QUANTA_START
s60_quanta_results:
        dc.b 'QI60'
        dc.l 0,0 ; phases, mismatched words
        dc.w 0,0 ; first failing phase and input-region byte offset
s60_quanta_expected: ds.b S60_QUANTA_BYTES
s60_test_quanta:
        move.l (s60_ticks,pc),d0
        cmp.l #QUANTA_TEST,d0
        bne .done
        move.l (s60_quanta_results+4,pc),d0
        bne .done
        movem.l d0-d7/a0-a6,-(sp)
        move.w (s60_phase,pc),-(sp)
        moveq #0,d5
.phase:
        lea (s60_phase,pc),a0
        move.w d5,(a0)
        bsr s60_quanta_reference
        move.l (s60_code,pc),a0
        adda.l #S60_QUANTA_START,a0
        lea (s60_quanta_expected,pc),a1
        move.w #S60_QUANTA_BYTES/2-1,d6
.copy:  move.w (a0)+,(a1)+
        dbf d6,.copy
        bsr s60_input_restore
        bsr s60_input_quanta
        IFD QUANTA_BAD
        move.l (s60_code,pc),a0
        adda.l #$1000f,a0
        eori.b #1,(a0)
        ENDC
        move.l (s60_code,pc),a0
        adda.l #S60_QUANTA_START,a0
        lea (s60_quanta_expected,pc),a1
        lea (s60_quanta_results,pc),a6
        moveq #0,d7
        move.w #S60_QUANTA_BYTES/2-1,d6
.compare:
        move.w (a0)+,d0
        cmp.w (a1)+,d0
        beq .same
        tst.l (8,a6)
        bne .error
        move.w d5,(12,a6)
        move.w d7,(14,a6)
.error: addq.l #1,(8,a6)
.same:  addq.w #2,d7
        dbf d6,.compare
        addq.l #1,(4,a6)
        addq.w #1,d5
        cmp.w #12,d5
        bcs .phase
        lea (s60_phase,pc),a0
        move.w (sp)+,(a0)
        bsr s60_input_quanta
        movem.l (sp)+,d0-d7/a0-a6
.done:  rts
; Unchanged table-loop reference, independent of the emitted fixed stores.
s60_quanta_reference:
        movem.l d0-d3/a0-a3,-(sp)
        move.l (s60_code,pc),a0
        lea (s60_input_sites,pc),a1
        lea (s60_input_values,pc),a2
        move.w (s60_phase,pc),d0
        adda.w d0,a2
.next:  move.l (a1)+,d1
        beq .done
        addq.l #2,a1
        move.w (a1)+,d2
        move.b (a2,d2.w),d3
        move.l a0,a3
        adda.l d1,a3
        move.b d3,(1,a3)
        bra .next
.done:  move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d3/a0-a3
        rts
        ENDC
        ENDC
