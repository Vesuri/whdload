        IFD VERIFY
        IFD POST_TEST
s60_post_results:
        dc.b 'U760'
        dc.w 0,0,0,0 ; death cases, quit cases, periodic substeps, errors
s60_post_counts: ds.w 4 ; spawn, boss-spawn, warning, quit request
s60_post_frame: ds.l 2
s60_post_expected: ds.b 64*16
s60_post_saved: ds.b 4*8
s60_post_energies: dc.w -32768,-1,0,32767
; Entire native entry instructions are replaced and restored by this fixture.
s60_post_gates:
        dc.l $3c14
        dc.w 8
        dc.l $4e55fff8
        dc.w s60_post_spawn-s60_post_gates
        dc.l $9346
        dc.w 8
        dc.l $2f0b4a39
        dc.w s60_post_boss-s60_post_gates
        dc.l $9986
        dc.w 6
        dc.l $4ef90002 ; relocated JMP operand: only opcode is checked below
        dc.w s60_post_sound-s60_post_gates
        dc.l $4184
        dc.w 6
        dc.l $4ef90001
        dc.w s60_post_quit-s60_post_gates
        dc.l 0
s60_post_gate:
        movem.l d1-d4/a0-a3,-(sp)
        move.w d0,d4
        lea (s60_post_gates,pc),a1
        lea (s60_post_saved,pc),a3
.next:  move.l (a1)+,d1
        beq .flush
        move.l (s60_code,pc),a0
        adda.l d1,a0
        move.w (a1)+,d2
        move.l (a1)+,d3
        move.w (a1)+,d1
        tst.w d4
        beq .restore
        cmp.w #6,d2
        beq .jmp_guard
        cmp.l (a0),d3
        bne s60_bad
        bra .save
.jmp_guard:
        cmp.w #$4ef9,(a0)
        bne s60_bad
.save:  move.l (a0),(a3)
        move.l (4,a0),(4,a3)
        lea (s60_post_gates,pc),a2
        adda.w d1,a2
        move.w #$4ef9,(a0)
        move.l a2,(2,a0)
        cmp.w #8,d2
        bne .advance
        move.w #$4e71,(6,a0)
        bra .advance
.restore:
        move.l (a3),(a0)
        move.w (4,a3),(4,a0)
        cmp.w #8,d2
        bne .advance
        move.w (6,a3),(6,a0)
.advance:
        addq.l #8,a3
        bra .next
.flush: move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d1-d4/a0-a3
        rts
s60_post_spawn:
        lea (s60_post_counts,pc),a0
        addq.w #1,(a0)
        rts
s60_post_boss:
        lea (s60_post_counts,pc),a0
        addq.w #1,(2,a0)
        rts
s60_post_sound:
        lea (s60_post_counts,pc),a0
        addq.w #1,(4,a0)
        rts
s60_post_quit:
        lea (s60_post_counts,pc),a0
        addq.w #1,(6,a0)
        clr.b ($1eb5-S60_DATA,a4)
        rts
s60_post_setup:
        lea (s60_post_counts,pc),a0
        clr.l (a0)+
        clr.l (a0)
        move.b #1,($1e53-S60_DATA,a4)
        clr.w ($1e90-S60_DATA,a4)
        clr.b ($1e56-S60_DATA,a4)
        clr.b ($1eb5-S60_DATA,a4)
        clr.w (-6,a5)
        move.w #1,($1e96-S60_DATA,a4)
        rts
s60_post_phase:
        moveq #0,d0
        tst.w d6
        bne .set
        moveq #1,d0
.set:   lea (s60_logic,pc),a0
        move.w d0,(a0)
        rts
s60_post_snapshot:
        lea (s60_post_counts,pc),a0
        move.l (a0)+,(a1)+
        move.l (a0),(a1)+
        move.w ($1e96-S60_DATA,a4),(a1)+
        move.w ($46c4-S60_DATA,a4),(a1)+
        move.w ($1e90-S60_DATA,a4),(a1)+
        move.b ($1e53-S60_DATA,a4),(a1)+
        move.b ($1e56-S60_DATA,a4),(a1)+
        rts
s60_post_actual: ds.b 16
s60_post_compare:
        lea (s60_post_actual,pc),a1
        bsr s60_post_snapshot
        lea (s60_post_actual,pc),a1
        move.l a2,a0
        moveq #3,d0
.next:  move.l (a0)+,d1
        cmp.l (a1)+,d1
        bne s60_post_error
        dbf d0,.next
        rts
s60_post_error:
        lea (s60_post_results,pc),a0
        addq.w #1,(10,a0)
        rts
s60_test_post:
        move.l (s60_ticks,pc),d0
        cmp.l #POST_TEST,d0
        bne .done
        movem.l d2-d7/a2-a6,-(sp)
        move.w (s60_logic,pc),-(sp)
        move.w ($1e52-S60_DATA,a4),-(sp)
        move.w ($1e56-S60_DATA,a4),-(sp)
        move.w ($1eb4-S60_DATA,a4),-(sp)
        move.w ($1e90-S60_DATA,a4),-(sp)
        move.w ($1e96-S60_DATA,a4),-(sp)
        move.w ($46c4-S60_DATA,a4),-(sp)
        lea (s60_post_frame+8,pc),a5
        moveq #1,d0
        bsr s60_post_gate
        moveq #0,d5
.energy:
        moveq #0,d6
.phase:
        bsr s60_post_setup
        bsr s60_post_phase
        lea (s60_post_energies,pc),a0
        move.w d5,d0
        add.w d0,d0
        move.w (a0,d0.w),($46c4-S60_DATA,a4)
        ; Untouched native death branch is the reference, including signed zero.
        S60_CALL $2cce
        lea (s60_post_expected,pc),a2
        move.l a2,a1
        bsr s60_post_snapshot
        bsr s60_post_setup
        S60_CALL $2c58
        bsr s60_post_compare
        lea (s60_post_results,pc),a0
        addq.w #1,(4,a0)
        addq.w #1,d6
        cmp.w #S60_SUBSTEPS,d6
        bne .phase
        addq.w #1,d5
        cmp.w #4,d5
        bne .energy
        ; Pending request must dispatch regardless of legacy phase. The native
        ; first-update guard suppresses exactly one call and then clears itself.
        moveq #0,d5
.guard:
        moveq #0,d6
.quit_phase:
        bsr s60_post_setup
        bsr s60_post_phase
        move.w #680,($46c4-S60_DATA,a4)
        move.b #1,($1eb5-S60_DATA,a4)
        move.w d5,(-6,a5)
        S60_CALL $2c58
        move.w (s60_post_counts+6,pc),d0
        moveq #1,d1
        sub.w d5,d1
        cmp.w d1,d0
        bne .quit_error
        tst.w (-6,a5)
        bne .quit_error
        S60_CALL $2c58
        move.w (s60_post_counts+6,pc),d0
        cmp.w #1,d0
        bne .quit_error
        tst.b ($1eb5-S60_DATA,a4)
        beq .quit_next
.quit_error:
        bsr s60_post_error
.quit_next:
        lea (s60_post_results,pc),a0
        addq.w #1,(6,a0)
        addq.w #1,d6
        cmp.w #S60_SUBSTEPS,d6
        bne .quit_phase
        addq.w #1,d5
        cmp.w #2,d5
        bne .guard
        ; Native periodic branch reference: 64 calls spanning word-counter wrap.
        ; Both frame masks (15/63), low-energy warning and callback counts are
        ; compared after every one of 64*N fractional calls below.
        bsr s60_post_setup
        move.w #199,($46c4-S60_DATA,a4)
        move.w #$ffe0,($1e96-S60_DATA,a4)
        moveq #0,d6
        bsr s60_post_phase
        lea (s60_post_expected,pc),a3
        moveq #63,d7
.reference:
        S60_CALL $2c96
        move.l a3,a1
        bsr s60_post_snapshot
        adda.w #16,a3
        dbf d7,.reference
        lea (s60_post_counts,pc),a0
        cmp.l #$00040004,(a0)
        bne .reference_error
        cmp.l #$00010000,(4,a0)
        bne .reference_error
        cmp.w #$20,($1e96-S60_DATA,a4)
        beq .reference_ok
.reference_error:
        bsr s60_post_error
.reference_ok:
        bsr s60_post_setup
        move.w #$ffe0,($1e96-S60_DATA,a4)
        lea (s60_post_expected,pc),a2
        moveq #63,d7
.interval:
        moveq #0,d6
.substep:
        bsr s60_post_phase
        S60_CALL $2c58
        bsr s60_post_compare
        lea (s60_post_results,pc),a0
        addq.w #1,(8,a0)
        addq.w #1,d6
        cmp.w #S60_SUBSTEPS,d6
        bne .substep
        adda.w #16,a2
        dbf d7,.interval
        moveq #0,d0
        bsr s60_post_gate
        move.w (sp)+,($46c4-S60_DATA,a4)
        move.w (sp)+,($1e96-S60_DATA,a4)
        move.w (sp)+,($1e90-S60_DATA,a4)
        move.w (sp)+,($1eb4-S60_DATA,a4)
        move.w (sp)+,($1e56-S60_DATA,a4)
        move.w (sp)+,($1e52-S60_DATA,a4)
        lea (s60_logic,pc),a0
        move.w (sp)+,(a0)
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
