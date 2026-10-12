; SPS 0481 candidate simulation/presentation split; not installed by the release.
; 68020 candidate; requires FerrariFormulaOne_UpdateHooks.s and its native sites.
; FF1InstallPresentation validates every new entry before patching. The host
; flushes the instruction cache after all installers, before resuming the game.
; FF1SimulationTail replaces the drawing-omission tail; clocks still execute at
; their original eligible tick sites. FF1PresentComponents may be called zero
; or more times between completed ticks; it never advances simulation state.
; Native bitplanes, blitter waits and rendering scratch remain presentation-owned.
; This is the component split, not the full road renderer or final scheduler.

FF1SimulationTail:
 movem.l d0-d7/a0-a6,-(sp)
 ; Animation rates have native 100 ms units, like recovery and filtered boost.
 tst.w events_pulse(pc)
 beq.b .recovery
 bsr.w FF1InstrumentTick
.recovery:
 bsr.w recovery_tick
 bsr.w boost_before
 tst.w d0
 beq.b .after
 lea FF1BoostSimulation(pc),a0
 move.w #1,(a0)
 move.w $66faa,d0
 ext.l d0
 move.l d0,-(sp)
 jsr $6bbfc
 addq.l #4,sp
 lea FF1BoostSimulation(pc),a0
 clr.w (a0)
.after:
 IFD VERIFY
 bsr.w boost_after
 ENDC
 movem.l (sp)+,d0-d7/a0-a6
 jmp $65d6e

FF1InstrumentTick:
 ; Extracted from h197's instrument entry and wheel phase block.
 tst.w $32b76
 beq.b .countdown
 move.w $32b74,d0
 move.w d0,$66c8a
 move.w d0,$66c88
.countdown:
 tst.w $66f94
 bne.b .done
 move.w $2275a,d0
 sub.w d0,$6c946
 move.w $6c944,d0
 add.w $66c8a,d0
 andi.w #2047,d0
 move.w d0,$6c944
 move.w $6c942,d0
 add.w $66c88,d0
 andi.w #2047,d0
 move.w d0,$6c942
.done:
 rts

FF1BoostEntry:
 link a6,#-16
 movem.l d2-d3,-(sp)
 tst.w FF1BoostSimulation(pc)
 bne.b .simulation
 ; The gauge uses the unfiltered RPM-derived height. Recompute this local
 ; drawing input without advancing boost, audio pitch/delta or gear position.
 move.w $6f270,d0
 ext.l d0
 divs.w #265,d0
 subi.w #15,d0
 bpl.b .height
 clr.w d0
.height:
 move.w d0,-6(a6)
 jmp $6bcc8
.simulation:
 jmp $6bc04

FF1BoostGauges:
 tst.w FF1BoostSimulation(pc)
 bne.b .simulation
 tst.w $32b76
 jmp $6bcce
.simulation:
 jmp $6be6a

FF1BoostGear:
 tst.w FF1BoostSimulation(pc)
 beq.b .presentation
 move.w $6f272,d0
 jmp $6be70
.presentation:
 jmp $6bf26

FF1BoostGearDraw:
 tst.w FF1BoostSimulation(pc)
 bne.b .simulation
 move.w 10(a6),d0
 ext.l d0
 jmp $6bf2c
.simulation:
 jmp $6bf60

FF1ClockTick:
 ; C stack ABI: clock pointer at 4(sp). Forward it to the unchanged native
 ; calendar arithmetic, suppressing only its digit renderer for this call.
 move.l 4(sp),-(sp)
 lea FF1ClockSimulation(pc),a0
 move.w #1,(a0)
 jsr $22c3a
 move.l a0,-(sp)
 lea FF1ClockSimulation(pc),a0
 clr.w (a0)
 move.l (sp)+,a0
 addq.l #4,sp
 rts

FF1ClockDigit:
 move.w ccr,-(sp)
 tst.w FF1ClockSimulation(pc)
 bne.b .simulation
 move.w (sp)+,ccr
 link a6,#0
 tst.w $235c8
 jmp $23292
.simulation:
 move.w (sp)+,ccr
 rts

FF1PresentComponents:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 ; Retain the native instrument/opponent renderer, including all DMA waits.
 move.w $6a66a,d0
 andi.w #1023,d0
 muls.w #2016,d0
 moveq #10,d1
 asr.l d1,d0
 move.l d0,-(sp)
 jsr $6c0d0
 addq.l #4,sp
 move.w $66faa,d0
 ext.l d0
 move.l d0,-(sp)
 jsr $6bbfc
 addq.l #4,sp
 bsr.w FF1PresentClock
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 rts

FF1PresentClock:
 movem.l d0-d7/a0-a6,-(sp)
 move.l $23bb0,-(sp)
 move.w $235c8,-(sp)
 move.l $23608,$23bb0
 clr.w $235c8
 ; Native display selection: calendar with date, or session with tenths.
 lea $226c0,a3
 lea FF1ClockCalendarDigits(pc),a2
 moveq #9,d7
 tst.w $1c1e8
 beq.b .next
 lea $226ca,a3
 lea FF1ClockSessionDigits(pc),a2
 moveq #6,d7
.next:
 ; Table entry: clock byte, 0=plain/1=tens/2=ones, x offset, date flag.
 moveq #0,d0
 move.b (a2)+,d0
 move.b (a3,d0.w),d0
 andi.l #255,d0
 moveq #0,d1
 move.b (a2)+,d1
 beq.b .value
 divu.w #10,d0
 subq.w #1,d1
 beq.b .value
 swap d0
.value:
 andi.l #$ffff,d0
 moveq #0,d1
 move.b (a2)+,d1
 tst.b (a2)+
 bne.b .date
 move.w $23612,d2
 add.w $23610,d1
 bra.b .draw
.date:
 move.w $2360e,d2
 add.w $2360c,d1
.draw:
 ext.l d1
 ext.l d2
 move.l d2,-(sp)
 move.l d1,-(sp)
 move.l d0,-(sp)
 jsr $23288
 lea 12(sp),sp
 dbra d7,.next
 move.w (sp)+,$235c8
 move.l (sp)+,$23bb0
 movem.l (sp)+,d0-d7/a0-a6
 rts
FF1ClockCalendarDigits:
 dc.b 3,0,0,0, 4,0,1,0, 5,0,3,0, 6,0,4,0
 dc.b 1,1,0,1, 1,2,1,1, 2,1,3,1, 2,2,4,1
 dc.b 0,1,6,1, 0,2,7,1
FF1ClockSessionDigits:
 dc.b 3,0,0,0, 4,0,1,0, 5,0,3,0, 6,0,4,0
 dc.b 7,0,6,0, 8,0,7,0, 9,0,9,0
 even
FF1BoostSimulation: dc.w 0
FF1ClockSimulation: dc.w 0
FF1PresentationInstalled: dc.l 0

FF1InstallPresentation:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #$4e56,$6bbfc
 bne.w .bad
 cmpi.w #$fff0,$6bbfe
 bne.w .bad
 cmpi.w #$48e7,$6bc00
 bne.w .bad
 cmpi.w #$3000,$6bc02
 bne.w .bad
 cmpi.w #$4a79,$6bcc8
 bne.w .bad
 cmpi.w #$0003,$6bcca
 bne.w .bad
 cmpi.w #$2b76,$6bccc
 bne.w .bad
 cmpi.w #$3039,$6be6a
 bne.w .bad
 cmpi.w #$0006,$6be6c
 bne.w .bad
 cmpi.w #$f272,$6be6e
 bne.w .bad
 cmpi.w #$302e,$6bf26
 bne.w .bad
 cmpi.w #$000a,$6bf28
 bne.w .bad
 cmpi.w #$48c0,$6bf2a
 bne.w .bad
 cmpi.w #$4e56,$23288
 bne.w .bad
 cmpi.w #$0000,$2328a
 bne.w .bad
 cmpi.w #$4a79,$2328c
 bne.w .bad
 cmpi.w #$0002,$2328e
 bne.w .bad
 cmpi.w #$35c8,$23290
 bne.w .bad
 cmpi.w #$4a79,$6c0d8
 bne.w .bad
 cmpi.w #$0003,$6c0da
 bne.w .bad
 cmpi.w #$2b76,$6c0dc
 bne.w .bad
 cmpi.w #$4a79,$6c2cc
 bne.w .bad
 cmpi.w #$0006,$6c2ce
 bne.w .bad
 cmpi.w #$6f94,$6c2d0
 bne.w .bad
 lea FF1BoostEntry(pc),a0
 move.l a0,$6bbfe
 move.w #$4ef9,$6bbfc
 move.w #$4e71,$6bc02
 lea FF1BoostGauges(pc),a0
 move.l a0,$6bcca
 move.w #$4ef9,$6bcc8
 lea FF1BoostGear(pc),a0
 move.l a0,$6be6c
 move.w #$4ef9,$6be6a
 lea FF1BoostGearDraw(pc),a0
 move.l a0,$6bf28
 move.w #$4ef9,$6bf26
 lea FF1ClockDigit(pc),a0
 move.l a0,$2328a
 move.w #$4ef9,$23288
 move.w #$4e71,$2328e
 move.w #$4e71,$23290
 move.l #$6c106,$6c0da
 move.w #$4ef9,$6c0d8
 move.l #$6c310,$6c2ce
 move.w #$4ef9,$6c2cc
 lea FF1PresentationInstalled(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #36,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
