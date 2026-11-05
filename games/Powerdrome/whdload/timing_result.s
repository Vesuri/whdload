; Latch a classified logical winning instant before result cleanup restores
; its clock ownership. Only the ordinary race-duration read uses this instant;
; display/input waits and unclassified result sources retain the native clock.
timing_result_begin
 move.w sr,-(sp)
 movem.l d0/a0,-(sp)
 lea timing_result_state(pc),a0
 clr.l 8(a0)
 addq.l #1,16(a0)
 tst.w 36(a0)
 beq.s .opponent_check
 clr.w 36(a0)
 move.w #1,8(a0)
 move.w #3,10(a0)
 move.l 40(a0),12(a0)
 bra.s .done
.opponent_check
 move.w timing_pit_opponent_state+10(pc),d0
 bne.s .opponent
 move.w timing_retune_state+10(pc),d0
 beq.s .done
 moveq #2,d0
 bra.s .latch
.opponent
 moveq #1,d0
.latch
 move.w #1,8(a0)
 move.w d0,10(a0)
 move.l timing_lap_current(pc),12(a0)
.done
 movem.l (sp)+,d0/a0
 move.w (sp)+,ccr
 rts

; Entry replaces the unique player-finish MOVE/BRA after native stack unwind.
; Capture this world's instant before BFB0 restores world ownership.
timing_result_player
 move.w sr,-(sp)
 movem.l d1/a0,-(sp)
 lea timing_result_state(pc),a0
 clr.w 36(a0)
 move.w timing_started(pc),d1
 beq.s .done
 move.w timing_world_state+8(pc),d1
 beq.s .done
 move.w timing_pit_opponent_state+8(pc),d1
 beq.s .done
 tst.w $be(a6)
 bne.s .done
 tst.w $b6(a6)
 bne.s .done
 tst.w $c0(a6)
 bne.s .done
 move.l timing_lap_state+24(pc),d1
 beq.s .done
 move.l timing_world20_clock(pc),d1
 move.l d1,48(a0)
 sub.l timing_pit_opponent_state+52(pc),d1
 add.l #TIMING_PERIOD,d1
 add.l timing_lap_state+8(pc),d1
 move.l d1,40(a0)
 move.w #1,36(a0)
 addq.l #1,44(a0)
.done
 movem.l (sp)+,d1/a0
 move.w (sp)+,ccr
 move.w #$ffff,d0
 bra.w timing_result_player_native

timing_result_player_native dc.w $4ef9
 dc.l 0

 IFNE TIMING_PLAYER_RESULT_TEST
; Admit the synthetic lap through the checkpoint predicate without rewriting it.
timing_result_player_test_checkpoint
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea timing_result_state(pc),a0
 tst.l 56(a0)
 beq.s .native
 tst.l 60(a0)
 bne.s .native
 addq.l #1,60(a0)
 movea.l (sp)+,a0
 move.w (sp)+,ccr
 tst.w $1b6(a6)
 bra.w timing_result_player_test_account
.native
 movea.l (sp)+,a0
 move.w (sp)+,ccr
 tst.w $1b6(a6)
 beq.w timing_result_player_test_reject
 bra.w timing_result_player_test_account

timing_result_player_test_account dc.w $4ef9
 dc.l 0
timing_result_player_test_reject dc.w $4ef9
 dc.l 0

; Test-only: force one lap-boundary decision after countdown completion.
; Native F952 executes with its original caller stack and performs all mutations.
timing_result_player_test_boundary
 move.w sr,-(sp)
 movem.l d1/a0,-(sp)
 lea timing_result_state(pc),a0
 tst.l 56(a0)
 bne.s .native
 tst.w $c0(a6)
 bne.s .native
 tst.w $be(a6)
 bne.s .native
 tst.w $b6(a6)
 bne.s .native
 tst.w $43a(a6)
 bpl.s .native
 move.w timing_world_state+8(pc),d1
 beq.s .native
 move.l timing_lap_state+24(pc),d1
 beq.s .native
 move.l timing_world20_clock(pc),d1
 sub.l timing_lap_state+28(pc),d1
 cmp.l #100,d1
 blo.s .native
 addq.l #1,56(a0)
 movem.l (sp)+,d1/a0
 move.w (sp)+,ccr
 cmp.w d0,d0
 bra.w timing_result_player_test_lap
.native
 movem.l (sp)+,d1/a0
 move.w (sp)+,ccr
 cmp.l (a3,d0.w),d4
 blt.w timing_result_player_test_no_lap
 bra.w timing_result_player_test_advance

timing_result_player_test_lap dc.w $4ef9
 dc.l 0
timing_result_player_test_no_lap dc.w $4ef9
 dc.l 0
timing_result_player_test_advance dc.w $4ef9
 dc.l 0

; Test-only: force one native player-result branch in an ordinary race.
; Do not rewrite lap counts, rankings, deadlines, seeds or stored durations.
timing_result_player_test
 move.w sr,-(sp)
 movem.l d1/a0,-(sp)
 lea timing_result_state(pc),a0
 tst.l 52(a0)
 bne.s .native
 tst.w $c0(a6)
 bne.s .native
 tst.w $be(a6)
 bne.s .native
 tst.w $b6(a6)
 bne.s .native
 move.w timing_world_state+8(pc),d1
 beq.s .native
 move.l timing_lap_state+24(pc),d1
 beq.s .native
 addq.l #1,52(a0)
 movem.l (sp)+,d1/a0
 move.w (sp)+,ccr
 cmp.w d0,d0
 bra.w timing_result_player_test_won
.native
 movem.l (sp)+,d1/a0
 move.w (sp)+,ccr
 cmp.w $266(a6),d0
 bne.w timing_result_player_test_continue
 bra.w timing_result_player_test_won

timing_result_player_test_won dc.w $4ef9
 dc.l 0
timing_result_player_test_continue dc.w $4ef9
 dc.l 0
 ENDC

timing_result_clock_d7
 move.w sr,-(sp)
 movem.l a0-a1,-(sp)
 lea timing_result_state(pc),a0
 IFD VERIFY
 move.w 8(sp),28(a0)
 ENDC
 addq.l #1,20(a0)
 move.l perf_game(pc),a1
 move.l $f96(a1),d7
 move.l d7,24(a0)
 tst.w 8(a0)
 beq.s .selected
 move.l 12(a0),d7
.selected
 move.l d7,32(a0)
 movem.l (sp)+,a0-a1
 move.w (sp)+,ccr
 ; Native MOVE.L sets NZVC and preserves X. Restore X before reproducing it.
 tst.l d7
 IFD VERIFY
 bsr timing_result_flags
 ENDC
 rts

 IFD VERIFY
timing_result_flags
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea timing_result_state(pc),a0
 move.w 4(sp),30(a0)
 movea.l (sp)+,a0
 move.w (sp)+,ccr
 rts
 ENDC

timing_result_state dc.b 'PDRSLT01'
 dc.w 0 ; logical winning instant valid until session cleanup
 dc.w 0 ; source: 0 native, 1 active opponent, 2 deferred pit opponent, 3 player
 dc.l 0 ; logical winning instant in the stable lap/race epoch
 dc.l 0 ; result entries
 dc.l 0 ; ordinary race-duration clock reads
 dc.l 0 ; native physical clock observed at the duration read
 dc.w 0 ; VERIFY guest input CCR
 dc.w 0 ; VERIFY guest output CCR
 dc.l 0 ; clock returned to the native duration calculation
 dc.w 0,0 ; pending player finish, padding
 dc.l 0 ; captured player winning instant
 dc.l 0 ; supported player finishes captured
 dc.l 0 ; captured player logical world timestamp
 dc.l 0 ; VERIFY-only forced player-result branches
 dc.l 0 ; VERIFY-only forced post-countdown lap boundaries
 dc.l 0 ; VERIFY-only forced checkpoint admissions
