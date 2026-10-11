; Experimental repair presentation extraction. All native geometry updates and
; E296's message/refuel/input/opponent service remain; only late pictures drop.
; Entry wrappers already save D0-D2/A0-A1/CCR around this decision.
timing_repair_choose_draw
 lea timing_repair_drop_state(pc),a0
 clr.w 8(a0)
 move.w timing_repair_state+8(pc),d0
 beq.s .done
 ; EC=0 bypasses the E2FC gate; retain its complete native presentation.
 tst.w $ec(a6)
 beq.s .draw
 tst.w $da(a6)
 beq.s .draw
 ; Always show stage endpoints and the first frame after the repair/sound event.
 cmp.w #32,d7
 beq.s .draw
 tst.w d7
 beq.s .draw
 move.w timing_repair_state+10(pc),d0
 beq.s .time
 cmp.w #31,d7
 beq.s .draw
.time
 bsr timing_clock
 move.l perf_game(pc),a1
 move.l $f96(a1),d0
 sub.l timing_repair_state+20(pc),d0
 move.l d0,28(a0)
 cmp.l #4,d0 ; one PAL field late relative to the preceding deadline
 blt.s .draw
 move.w #1,8(a0)
 addq.l #1,12(a0)
 IFNE TIMING_REPAIR_INPUT_TEST
 bsr timing_repair_input_test
 ENDC
 rts
.draw
 addq.l #1,24(a0)
.done
 rts

; The original clip call can discard its own return slot when clipped out.
; Keep precisely that call depth; no saved register remains beneath it.
; Suppression is limited to the selected repair drawing interval and cleared
; before E296's input/opponent tail, including any native nonlocal result exit.
timing_repair_bitmap
 move.l a0,-(sp)
 lea timing_repair_drop_state(pc),a0
 tst.w 8(a0)
 beq.s .native
 addq.l #1,16(a0)
 movea.l (sp)+,a0
 rts
.native
 movea.l (sp)+,a0
 bsr timing_repair_clip
 move.l #255,d7
 bra.w timing_repair_bitmap_continue

; Native message expiry and elapsed refueling precede this boundary. Skipping
; the whole presentation avoids both the buffer exchange and background copy.
; The native successor MOVE.L #191,D0 replaces NZVC; this gate preserves X.
timing_repair_present_gate
 move.l a0,-(sp)
 lea timing_repair_drop_state(pc),a0
 tst.w 8(a0)
 bne.s .skip
 movea.l (sp)+,a0
 move.l perf_game(pc),a0
 movea.l $706(a0),a0
 bra.w timing_repair_present_continue
.skip
 movea.l (sp)+,a0
 bsr timing_clock
 bra.w timing_repair_service_entry

; Replay the native mode branch, retaining its original saved D0-A5 frame.
; A dropped picture omits the HUD drawing call too, then rejoins before the
; native counter, timeout, input, opponent and keyboard operations.
timing_repair_service_gate
 move.l a0,-(sp)
 lea timing_repair_drop_state(pc),a0
 tst.w 8(a0)
 beq.s .native
 clr.w 8(a0)
 addq.l #1,20(a0)
 movea.l (sp)+,a0
 tst.w $da(a6)
 beq.w timing_repair_service_return
 bra.w timing_repair_service_continue
.native
 movea.l (sp)+,a0
 tst.w $da(a6)
 beq.w timing_repair_service_return
 bra.w timing_repair_service_draw

timing_repair_clip dc.w $4ef9
 dc.l 0
timing_repair_bitmap_continue dc.w $4ef9
 dc.l 0
timing_repair_present_continue dc.w $4ef9
 dc.l 0
timing_repair_service_entry dc.w $4ef9
 dc.l 0
timing_repair_service_return dc.w $4ef9
 dc.l 0
timing_repair_service_draw dc.w $4ef9
 dc.l 0
timing_repair_service_continue dc.w $4ef9
 dc.l 0

timing_repair_drop_state dc.b 'PDRDROP1'
 dc.w 0,0 ; suppression active, reserved
 dc.l 0 ; late steps selected for suppression
 dc.l 0 ; bitmap calls suppressed
 dc.l 0 ; native service-only continuations
 dc.l 0 ; steps selected for drawing
 dc.l 0 ; last signed lateness at step entry

 IFNE TIMING_REPAIR_INPUT_TEST
; Input-only directed fixture: publish one ordinary key into the native ring
; on the first dropped repair step. No physics, timing or mode fields are set.
; Wait for the regular coverage tape to finish and an empty native queue.
timing_repair_input_test
 movem.l d0-d2/a0-a2,-(sp)
 move.l custom5(pc),d0
 cmp.l #13,d0
 bne.s .done
 move.w cov_done(pc),d0
 beq.s .done
 lea timing_repair_input_state(pc),a1
 tst.w 8(a1)
 bne.s .done
 move.l perf_game(pc),a0
 move.w $461a(a0),d0
 cmp.w $461c(a0),d0
 bne.s .done
 move.w d0,12(a1)
 move.w d0,14(a1)
 lea $460a(a0),a2
 move.b #'x',(a2,d0.w)
 addq.w #1,d0
 cmp.w $4608(a0),d0
 blo.s .head
 moveq #0,d0
.head
 move.w d0,$461a(a0)
 move.w d0,16(a1)
 move.w #'x',10(a1)
 move.w #1,8(a1)
.done
 movem.l (sp)+,d0-d2/a0-a2
 rts

timing_repair_input_state dc.b 'PDRKEY01'
 dc.w 0,0 ; publications, key
 dc.w 0,0,0 ; old reader, old writer, new writer
 even
 ENDC
