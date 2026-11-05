; Development-only cockpit departure pacing. Native nine-step geometry is retained.
; A500 measured movement intervals are five PAL fields / 20 native clock units.
DEPARTURE_PERIOD = 20
install_departure
 movem.l d0/a0-a2,-(sp)
 move.l perf_game(pc),a1
 move.l a1,a0
 adda.l #$102d0,a0
 cmp.l #$d640d841,(a0)
 bne.s .wrong
 cmp.w #$da42,4(a0)
 bne.s .wrong
 cmp.w #$4eb9,$48(a0)
 bne.s .wrong
 move.l a1,d0
 add.l #$8056,d0
 cmp.l $4a(a0),d0
 bne.s .wrong
 move.l a1,d0
 add.l #$59b6,d0
 lea departure_clock+2(pc),a0
 move.l d0,(a0)
 move.l a1,d0
 add.l #$102d6,d0
 lea departure_continue+2(pc),a0
 move.l d0,(a0)
 move.l a1,d0
 add.l #$8056,d0
 lea departure_native_present+2(pc),a0
 move.l d0,(a0)
 lea pl_departure(pc),a0
 move.l _resload(pc),a2
 jsr resload_Patch(a2)
 movem.l (sp)+,d0/a0-a2
 rts
.wrong
 pea TDREASON_WRONGVER
 move.l _resload(pc),a2
 jmp resload_Abort(a2)
pl_departure PL_START
 ; Three complete ADD.W instructions; replayed after initializing the deadline.
 ; TIMING_RANGE h0:$102d0 6 bit=C3
 PL_P $102d0,departure_step
 ; Native presentation call, after this step's view has been drawn.
 ; TIMING_RANGE h0:$10318 6 bit=C3
 PL_PS $10318,departure_present
 PL_END

departure_step
 cmp.w #8,d7
 bne.s .advance
 movem.l d0-d1/a0-a1,-(sp)
 bsr departure_clock
 move.l perf_game(pc),a0
 move.l $f96(a0),d0
 add.l #DEPARTURE_PERIOD,d0
 lea departure_deadline(pc),a1
 move.l d0,(a1)
 movem.l (sp)+,d0-d1/a0-a1
.advance
 add.w d0,d3
 add.w d1,d4
 add.w d2,d5
 bra.w departure_continue

departure_present
 movem.l d0-d1/a0-a1,-(sp)
 move.l perf_game(pc),a0
 lea departure_deadline(pc),a1
.wait
 bsr departure_clock
 move.l $f96(a0),d0
 sub.l (a1),d0
 bmi.s .wait
 ; Advance the deadline, not the observed clock: retain fractional lateness.
 add.l #DEPARTURE_PERIOD,(a1)
 movem.l (sp)+,d0-d1/a0-a1
 bra.w departure_native_present

departure_clock dc.w $4ef9
 dc.l 0
departure_continue dc.w $4ef9
 dc.l 0
departure_native_present dc.w $4ef9
 dc.l 0
departure_deadline dc.l 0
