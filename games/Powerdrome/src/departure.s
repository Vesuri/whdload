; Cockpit departure pacing. Native nine-step geometry is retained.
; A500 measured movement intervals are five PAL fields / 20 native clock units.
; DEPARTURE_INTERPOLATE draws extra views between steps at positions blended from the
; previous to the current step, while the time allows; the step itself is still presented
; at its deadline with the exact native position. 0 keeps the step-only presentation.
DEPARTURE_PERIOD = 20
 IFND DEPARTURE_INTERPOLATE
DEPARTURE_INTERPOLATE = 1
 ENDC
install_departure
 movem.l d0/a0-a2,-(sp)
 move.l perf_game(pc),a1
 move.l a1,a0
 adda.l #$102d0,a0
 cmp.l #$d640d841,(a0)
 bne.w .wrong
 cmp.w #$da42,4(a0)
 bne.w .wrong
 cmp.w #$4eb9,$48(a0)
 bne.w .wrong
 move.l a1,d0
 add.l #$8056,d0
 cmp.l $4a(a0),d0
 bne.w .wrong
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
 IFNE DEPARTURE_INTERPOLATE
 ; The views $10314/$1030e call: the regular departure view and the low-altitude one.
 move.l a1,a0
 adda.l #$10300,a0
 cmp.l #$61000022,$14(a0)
 bne.w .wrong
 cmp.l #$6100541e,$e(a0)
 bne.w .wrong
 move.l a1,d0
 add.l #$10338,d0
 lea departure_native_view+2(pc),a0
 move.l d0,(a0)
 move.l a1,d0
 add.l #$1572e,d0
 lea departure_native_low_view+2(pc),a0
 move.l d0,(a0)
 ENDC
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
 IFNE DEPARTURE_INTERPOLATE
 ; MOVE.W 302(a6),d0 + CMP.W #-140,d0 before the view choice; replayed with its flags.
 ; TIMING_RANGE h0:$10304 8 bit=C3
 PL_PS $10304,departure_blend
 PL_NOP $1030a,2
 ENDC
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
 IFNE DEPARTURE_INTERPOLATE
 move.l a0,-(sp)
 lea departure_previous(pc),a0
 movem.w d3-d5,(a0)
 ENDC
 add.w d0,d3
 add.w d1,d4
 add.w d2,d5
 IFNE DEPARTURE_INTERPOLATE
 lea departure_current(pc),a0
 movem.w d3-d5,(a0)
 movea.l (sp)+,a0
 ENDC
 bra.w departure_continue

departure_present
 movem.l d0-d1/a0-a1,-(sp)
 move.l perf_game(pc),a0
 lea departure_deadline(pc),a1
 IFD DEPARTURE_DIAGNOSTICS
 bsr departure_clock
 move.l $f96(a0),d0
 sub.l departure_stats+24(pc),d0
 move.l d0,departure_stats+20-departure_deadline(a1)
 ENDC
.wait
 bsr departure_clock
 move.l $f96(a0),d0
 sub.l (a1),d0
 bmi.s .wait
 ; Advance the deadline, not the observed clock: retain fractional lateness.
 add.l #DEPARTURE_PERIOD,(a1)
 movem.l (sp)+,d0-d1/a0-a1
 bra.w departure_native_present

 IFNE DEPARTURE_INTERPOLATE
; Before the step's native view: the previous step was presented at the previous
; deadline. While one blended view and the native view still fit before this step's
; deadline, draw and present the view for the time it is drawn at. The native view then
; draws the exact step position, presented at the deadline as without blending.
departure_blend
 movem.l d0-d7/a0-a5,-(sp)
 move.l perf_game(pc),a5
 lea departure_deadline(pc),a4
 lea departure_stats(pc),a3
 addq.l #1,8(a3)
.frame
 bsr departure_clock
 move.l (a4),d0
 sub.l $f96(a5),d0
 move.l d0,12(a3)
 move.l (a3),d1
 add.l d1,d1
 cmp.l d1,d0
 ble.s .native
 ; Elapsed time at presentation, one view's cost from now.
 moveq #DEPARTURE_PERIOD,d1
 sub.l d0,d1
 add.l (a3),d1
 cmp.l #DEPARTURE_PERIOD,d1
 blt.s .elapsed
 moveq #DEPARTURE_PERIOD,d1
.elapsed
 move.l $f96(a5),d6
 bsr departure_view
 IFD DEPARTURE_DIAGNOSTICS
 bsr departure_clock
 move.l $f96(a5),d0
 sub.l d6,d0
 move.l d0,16(a3)
 ENDC
 ; The native presentation does not preserve registers.
 movem.l d6/a3-a5,-(sp)
 bsr departure_native_present
 movem.l (sp)+,d6/a3-a5
 bsr departure_clock
 move.l $f96(a5),d0
 sub.l d6,d0
 move.l d0,(a3)
 addq.l #1,4(a3)
 bra.s .frame
.native
 ; Restore the exact position for the native view and replay the two instructions.
 moveq #DEPARTURE_PERIOD,d1
 bsr departure_place
 IFD DEPARTURE_DIAGNOSTICS
 bsr departure_clock
 move.l $f96(a5),24(a3)
 ENDC
 movem.l (sp)+,d0-d7/a0-a5
 move.w $12e(a6),d0
 cmp.w #-140,d0
 rts

; d1.l elapsed clock units (0..DEPARTURE_PERIOD): publish the blended position as the
; native loop does ($12c..$130 and negated at $3ac..$3b0).
departure_place
 movem.l d0-d3/a0-a3,-(sp)
 lea departure_previous(pc),a0
 lea departure_current(pc),a1
 moveq #2,d2
 lea $12c(a6),a2
 lea $3ac(a6),a3
.axis
 move.w (a1)+,d0
 move.w (a0)+,d3
 sub.w d3,d0
 muls.w d1,d0
 divs.w #DEPARTURE_PERIOD,d0
 add.w d3,d0
 move.w d0,(a2)+
 neg.w d0
 move.w d0,(a3)+
 dbra d2,.axis
 movem.l (sp)+,d0-d3/a0-a3
 rts

; Draw the view the native loop selects for the blended height. The frame counter is
; presentation-only here, so it keeps the native per-step count.
departure_view
 bsr.s departure_place
 movem.l d0-d7/a0-a5,-(sp)
 move.l $5e(a6),-(sp)
 cmp.w #-140,$12e(a6)
 bgt.s .regular
 bsr departure_native_low_view
 bra.s .drawn
.regular
 bsr departure_native_view
.drawn
 move.l (sp)+,$5e(a6)
 movem.l (sp)+,d0-d7/a0-a5
 rts

departure_native_view dc.w $4ef9
 dc.l 0
departure_native_low_view dc.w $4ef9
 dc.l 0
departure_previous ds.w 3
departure_current ds.w 3
departure_tag dc.b 'PDDEPI01'
; Clock units the last blended view and its presentation took (starts at one field),
; and the number of blended views presented.
departure_stats dc.l 4,0,0,0
 IFD DEPARTURE_DIAGNOSTICS
; Last blended view alone, native view, and the clock when the native view started.
 dc.l 0,0,0
 ENDC
 ENDC

departure_clock dc.w $4ef9
 dc.l 0
departure_continue dc.w $4ef9
 dc.l 0
departure_native_present dc.w $4ef9
 dc.l 0
departure_deadline dc.l 0
