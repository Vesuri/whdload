 IFND TIMING_DEPARTURE
TIMING_DEPARTURE = 1
 ENDC
 IFND TIMING_PERIODIC
TIMING_PERIODIC = 0
 ENDC
; C3: elapsed-time timing correction, independent of fast planar rendering.
; Current corrections: PAL minimum delta and A500-paced cockpit departure.
; Broader periodic gameplay scheduling remains a separately compiled prototype.
install_timing
 movem.l d0/a0-a2,-(sp)
 move.l custom3(pc),d0
 beq.s .done
 move.l perf_game(pc),a1
 lea $7f8e(a1),a0
 cmp.w #$bcbc,(a0)
 bne.s .wrong
 cmp.l #8,2(a0)
 bne.s .wrong
 cmp.w #$7c08,8(a0)
 bne.s .wrong
 lea pl_timing(pc),a0
 move.l _resload(pc),a2
 jsr resload_Patch(a2)
 IFNE TIMING_PERIODIC
 bsr install_periodic
 ENDC
 IFNE TIMING_DEPARTURE
 bsr install_departure
 ENDC
.done
 movem.l (sp)+,d0/a0-a2
 rts
.wrong
 pea TDREASON_WRONGVER
 move.l _resload(pc),a2
 jmp resload_Abort(a2)
pl_timing PL_START
 ; TIMING_RANGE h0:$7f8e 6 bit=C3 (comparison including patched immediate)
 PL_L $7f90,4
 ; TIMING_RANGE h0:$7f96 2 bit=C3 (MOVEQ #4,D6)
 PL_W $7f96,$7c04
 PL_END
 IFNE TIMING_PERIODIC
 INCLUDE periodic.s
 ENDC
 IFNE TIMING_DEPARTURE
 INCLUDE departure.s
 ENDC
