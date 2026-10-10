; Experimental PAL movement clock: nested presentations cannot overwrite elapsed
; time between movement updates. Retains native 20..250 ms clamp and speed scaling.
timing_movement_clock
 move.w sr,-(sp)
 movem.l d0-d2/a0-a1,-(sp)
 lea timing_movement_state(pc),a1
 move.l perf_game(pc),a0
 move.l $48fe(a0),d0
 sub.l timing_input_paused_fields(pc),d0
 lsl.l #2,d0
 move.l d0,d1
 sub.l 12(a1),d1
 move.l d0,12(a1)
 tst.w 8(a1)
 bne.s .elapsed
 move.w #1,8(a1)
 ; First movement retains its native pre-entry interval; no earlier cursor exists.
 moveq #0,d1
 move.w $21c(a6),d1
.elapsed
 move.l d1,16(a1)
 addq.l #1,24(a1)
 move.l d1,d2
 cmp.l #4,d1
 bge.s .upper
 moveq #4,d1
 bra.s .apply
.upper
 cmp.l #50,d1
 ble.s .apply
 moveq #50,d1
 sub.l d1,d2
 add.l d2,28(a1)
.apply
 move.w d1,20(a1)
 move.w d1,$21c(a6)
 movem.l (sp)+,d0-d2/a0-a1
 move.w (sp)+,ccr
 ; Replay displaced native MOVE/MULS, including their flags and signed arithmetic.
 move.w $194(a6),d4
 muls.w $21c(a6),d4
 ; Read architectural flags in the guest; debugger register snapshots may expose
 ; lazily materialized emulator flags. MOVEM/LEA/MOVE SR leave these unchanged.
 movem.l a0,-(sp)
 lea timing_movement_flags(pc),a0
timing_movement_read_flags
 move.w sr,(a0)
 movem.l (sp)+,a0
 bra.w timing_movement_continue

timing_movement_continue dc.w $4ef9
 dc.l 0

timing_movement_state dc.b 'PDMCLK02'
timing_movement_started dc.w 0
 dc.w 0
 dc.l 0 ; last unpaused VBL clock, in native five-ms units
 dc.l 0 ; most recent raw elapsed interval
 dc.w 0 ; applied interval
 dc.w 0
 dc.l 0 ; movement updates
 dc.l 0 ; elapsed units discarded above the retained 250-ms ceiling
timing_movement_flags dc.w 0
