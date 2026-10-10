; VERIFY-only input replay. Native input queues, modifiers and sampled buttons only.
pl_coverage PL_START
 ; Whole six-byte instructions; original VBL ADDQ is copied below.
 PL_PS $5780,coverage_vbl
 PL_PS $ca3e,coverage_start
 PL_END
install_coverage_patches
 movem.l d0/a0-a2,-(sp)
 move.l custom5(pc),d0
 cmp.l #3,d0
 blo.s .done
 bsr install_coverage
 lea pl_coverage(pc),a0
 move.l perf_game(pc),a1
 move.l _resload(pc),a2
 jsr resload_Patch(a2)
.done
 movem.l (sp)+,d0/a0-a2
 rts
install_coverage
 movem.l d0/a0-a1,-(sp)
 move.l perf_game(pc),a0
 lea $5780(a0),a0
 lea coverage_vbl_native(pc),a1
 move.l (a0)+,(a1)+
 move.w (a0),(a1)
 move.l (4).w,a0
 btst #AFB_68010,AttnFlags+1(a0)
 beq.s .flags_done
 lea coverage_start(pc),a0
 move.w #$42e7,(a0)
.flags_done
 movem.l (sp)+,d0/a0-a1
 rts
coverage_start
 move.w sr,-(sp)
 movem.l d0/a0-a1,-(sp)
 lea coverage_status(pc),a1
 addq.l #1,cov_flights-coverage_status(a1)
 lea pit_sent(pc),a0
 clr.w (a0)
 lea practice_sent(pc),a0
 clr.w (a0)
 tst.w cov_started-coverage_status(a1)
 bne.s .done
 move.w #1,cov_started-coverage_status(a1)
 move.l perf_game(pc),a0
 move.l $48fe(a0),cov_epoch-coverage_status(a1)
.done
 movem.l (sp)+,d0/a0-a1
 move.w (sp)+,ccr
 move.l perf_game(pc),a6
 lea $a6e(a6),a6
 rts
coverage_vbl
 movem.l d0-d3/a0-a2,-(sp)
 move.l perf_game(pc),a0
 lea coverage_status(pc),a1
 tst.w cov_started-coverage_status(a1)
 beq.w .done
 move.w cov_shift-coverage_status(a1),$f9e(a0)
 move.w cov_buttons-coverage_status(a1),$a6e+$432(a0)
 tst.w cov_done-coverage_status(a1)
 bne.w .done
 ; Timing fixture writes sampled native mouse inputs, never physics state.
 move.l custom5(pc),d0
 cmp.l #7,d0
 bne.s .normal_axes
 move.l $48fe(a0),d0
 sub.l cov_epoch-coverage_status(a1),d0
 clr.w $a6e+$42a(a0)
 clr.w $a6e+$42e(a0)
 cmp.l #160,d0
 blo.s .normal_axes
 cmp.l #220,d0
 bhs.s .normal_axes
 move.w #40,$a6e+$42a(a0)
 cmp.l #190,d0
 blo.s .normal_axes
 move.w #-40,$a6e+$42a(a0)
.normal_axes
 lea coverage_tape(pc),a2
 move.l custom5(pc),d0
 cmp.l #8,d0
 bne.s .not_pause
 lea coverage_timing_pause_tape(pc),a2
 bra.s .tape
.not_pause
 cmp.l #7,d0
 bne.s .not_timing
 lea coverage_timing_tape(pc),a2
 bra.s .tape
.not_timing
 cmp.l #5,d0
 blo.s .tape
 lea coverage_cruise(pc),a2
.tape
 adda.l cov_index-coverage_status(a1),a2
 move.l $48fe(a0),d0
 sub.l cov_epoch-coverage_status(a1),d0
 cmp.l (a2),d0
 blo.s .done
 move.w $461a(a0),d1
 cmp.w $461c(a0),d1
 bne.s .done
 move.w 6(a2),cov_shift-coverage_status(a1)
 move.w 8(a2),cov_buttons-coverage_status(a1)
 ; Publish the new modifiers before making its key visible.
 move.w 6(a2),$f9e(a0)
 move.w 8(a2),$a6e+$432(a0)
 move.w 4(a2),d2
 bmi.s .finished
 beq.s .advance
 lea $460a(a0),a2
 move.b d2,(a2,d1.w)
 addq.w #1,d1
 cmp.w $4608(a0),d1
 blo.s .head
 moveq #0,d1
.head
 move.w d1,$461a(a0)
 addq.l #1,cov_keys-coverage_status(a1)
.advance
 add.l #10,cov_index-coverage_status(a1)
 bra.s .done
.finished
 move.w #1,cov_done-coverage_status(a1)
.done
 movem.l (sp)+,d0-d3/a0-a2
coverage_vbl_native
 ds.b 6
 rts
 ; Called only after scene_entry saved every register and CCR.
coverage_fallback
 lea coverage_status(pc),a0
 addq.l #1,cov_native-coverage_status(a0)
 tst.w $2ea(a6)
 beq.s .inset
 addq.l #1,cov_full-coverage_status(a0)
.inset
 tst.w $2f2(a6)
 beq.s .effect
 addq.l #1,cov_inset-coverage_status(a0)
.effect
 move.w $4ce(a6),d0
 or.w $4d0(a6),d0
 beq.s .animation
 addq.l #1,cov_effect-coverage_status(a0)
.animation
 move.w $aa(a6),d0
 or.w $e6(a6),d0
 beq.s .done
 addq.l #1,cov_animation-coverage_status(a0)
.done
 rts
coverage_status dc.b 'PDCOV002'
cov_started dc.w 0
cov_done dc.w 0
cov_epoch dc.l 0
cov_index dc.l 0
cov_keys dc.l 0
cov_flights dc.l 0
cov_shift dc.w 0
cov_buttons dc.w 0
cov_native dc.l 0
cov_full dc.l 0
cov_inset dc.l 0
cov_effect dc.l 0
cov_animation dc.l 0
coverage_tape
 ; PAL-field offset, ASCII (0 controls only, -1 finish), Shift mask, mouse buttons.
 dc.l 10
 dc.w 'c',1,1
 dc.l 30
 dc.w 'c',1,1
 dc.l 50
 dc.w 'c',1,1
 dc.l 70
 dc.w 'c',1,1
 dc.l 90
 dc.w 'c',1,1
 dc.l 110
 dc.w 'c',1,1
 dc.l 130
 dc.w 'c',1,1
 dc.l 150
 dc.w 'c',1,1
 dc.l 170
 dc.w 'c',1,0
 dc.l 500
 dc.w 'v',1,0
 dc.l 800
 dc.w 'v',1,0
 dc.l 1000
 dc.w 'r',1,0
 dc.l 1300
 dc.w 'r',1,0
 dc.l 1500
 dc.w 't',1,0
 dc.l 1700
 dc.w 'p',1,0
 dc.l 1900
 dc.w 'l',1,0
 dc.l 2100
 dc.w 's',1,0
 dc.l 2150
 dc.w 's',1,0
 dc.l 2400
 dc.w 'z',0,3
 dc.l 4500
 dc.w 'a',0,3
 dc.l 7000
 dc.w 'b',0,2
 dc.l 8000
 dc.w 'b',0,2
 dc.l 18000
 dc.w 'q',2,0
 dc.l 18500
 dc.w 0,0,0
 dc.l 60000
 dc.w 'q',2,0
 dc.l 62000
 dc.w 0,0,0
 dc.l 65000
 dc.w -1,0,0

; On later pit visits, request native repairs before Space. No damage writes.
coverage_pit_ready
 moveq #0,d0
 move.w cov_started(pc),d0
 beq.s .done
 move.w pit_sent(pc),d0
 cmp.w #6,d0
 blo.s .ready
 moveq #0,d0
 rts
.ready
 moveq #-1,d0
.done
 rts
coverage_pit_key
 moveq #0,d0
 move.w cov_started(pc),d0
 beq.s .done
 movem.l d1/a0,-(sp)
 lea pit_sent(pc),a0
 move.w (a0),d1
 addq.w #1,(a0)
 lea coverage_repairs(pc),a0
 move.b (a0,d1.w),d0
 movem.l (sp)+,d1/a0
.done
 rts
coverage_repairs dc.b '13846 '
 EVEN

; Native qualifying exit, then sustained assisted flight in the race.
coverage_cruise
 dc.l 10
 dc.w 'q',2,0
 dc.l 100
 dc.w 0,0,0
 dc.l 2000
 dc.w 'c',1,1
 dc.l 2030
 dc.w 'c',1,1
 dc.l 2060
 dc.w 'c',1,1
 dc.l 2090
 dc.w 'c',1,1
 dc.l 2120
 dc.w 'c',1,1
 dc.l 2150
 dc.w 'c',1,1
 dc.l 2180
 dc.w 'c',1,1
 dc.l 2210
 dc.w 'c',1,1
 dc.l 2240
 dc.w 'c',1,1
 dc.l 3400
 dc.w 0,1,0
 dc.l 6000
 dc.w 'a',1,1
 dc.l 6500
 dc.w 0,1,0
 dc.l 9000
 dc.w 'a',1,1
 dc.l 9500
 dc.w 0,1,0
 dc.l 12000
 dc.w 'a',1,1
 dc.l 12500
 dc.w 0,1,0
 dc.l 15000
 dc.w 'a',1,1
 dc.l 15500
 dc.w 0,1,0
 dc.l 18000
 dc.w 'a',1,1
 dc.l 18500
 dc.w 0,1,0
 dc.l 21000
 dc.w 'a',1,1
 dc.l 21500
 dc.w 0,1,0
 dc.l 24000
 dc.w 'a',1,1
 dc.l 24500
 dc.w 0,1,0
 dc.l 27000
 dc.w 'a',1,1
 dc.l 27500
 dc.w 0,1,0
 dc.l 33000
 dc.w -1,0,0

; Select track index two with two ordinary menu-cycle keys, then Race.
coverage_menu_ready
 move.w cov_started(pc),d0
 bne.s .regular
 move.w practice_sent(pc),d0
 cmp.w #3,d0
 blo.s .ready
 moveq #0,d0
 rts
.regular
 move.w practice_sent(pc),d0
 beq.s .ready
 moveq #0,d0
 rts
.ready
 moveq #-1,d0
 rts
coverage_menu_key
 move.l a0,-(sp)
 lea practice_sent(pc),a0
 addq.w #1,(a0)
 move.w cov_started(pc),d0
 bne.s .race
 cmp.w #3,(a0)
 bhs.s .race
 move.l (sp)+,a0
 moveq #'0',d0
 rts
.race
 move.l (sp)+,a0
 moveq #'4',d0
 rts

; Short response fixture: throttle, brake, then a short left/right mouse input.
coverage_timing_tape
 dc.l 10
 dc.w 0,0,1
 dc.l 100
 dc.w 0,0,2
 dc.l 150
 dc.w 0,0,0
 dc.l 250
 dc.w -1,0,0


; Same acceleration/brake start, then native pause with input changes during the pause.
coverage_timing_pause_tape
 dc.l 10
 dc.w 0,0,1
 dc.l 100
 dc.w 0,0,2
 dc.l 150
 dc.w 0,0,0
 dc.l 160
 dc.w 's',1,0
 dc.l 175
 dc.w 0,1,1
 dc.l 190
 dc.w 0,1,2
 dc.l 200
 dc.w 0,1,0
 dc.l 210
 dc.w 's',1,0
 dc.l 260
 dc.w -1,0,0
