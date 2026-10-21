; D5a/b, enhanced 0658 only. Retain waits before blitter register changes,
; CPU mask writes, pixel reads/writes and display publication. The final
; polygon wait adds no protection beyond those consumers' own waits.
draw_overhead_install:
 movem.l d1/a0-a3,-(sp)
 movea.l RT_HUNKS(a0),a1
 movea.l a1,a3
 adda.l #$8820,a3
 cmpi.w #$41f9,(a3)
 bne .bad
 move.l a1,d0
 addi.l #$8d88,d0
 cmp.l 2(a3),d0
 bne .bad
 cmpi.l #$203cffff,6(a3)
 bne .bad
 cmpi.w #0,10(a3)
 bne .bad
 cmpi.w #$6004,32(a3)
 bne .bad
 movea.l a1,a3
 adda.l #$8d7a,a3
 cmpi.w #$4eb9,(a3)
 bne .bad
 lea blitter_wait(pc),a0
 cmpa.l 2(a3),a0
 bne .bad
 cmpi.w #$4e71,6(a3)
 bne .bad
 cmpi.l #$4cdf6f00,8(a3)
 bne .bad
 movea.l a1,a3
 adda.l #$8842,a3
 cmpi.l #$48e701e2,(a3)
 bne .bad
 cmpi.w #$3a39,4(a3)
 bne .bad
 lea draw_overhead_mask_begin(pc),a0
 move.l 4(a3),(a0)+
 move.w 8(a3),(a0)+
 move.w #$4ef9,(a0)+
 adda.w #10,a3
 move.l a3,(a0)
 lea draw_overhead_h0(pc),a0
 move.l a1,(a0)
 clr.w 4(a0)
 lea .patches(pc),a0
 jsr resload_Patch(a2)
 moveq #0,d0
 bra .done
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,d1/a0-a3
 rts
.patches:
 PL_START
 PL_P $8820,draw_overhead_native_begin
 PL_P $8842,draw_overhead_text_begin
 ; A completed BTST wait sets only Z. Preserve that return-flag contract.
 PL_L $8d7a,$003c0004 ; ORI #4,CCR
 PL_NOP $8d7e,4
 PL_END

; Native +8818 already saved d7/a0-a2/a6 and loaded d2. Continue at
; +8846 to clear the old chip mask and reset both native bounding boxes.
draw_overhead_native_begin:
 bsr draw_overhead_clear_spans
 move.l #$ffff0000,d0
 moveq #-1,d2
 bra draw_overhead_mask_begin

; Text enters the mask-clear path directly and resets the same bbox. Clear
; its preceding polygon's rows before those bounds are discarded as well.
draw_overhead_text_begin:
 movem.l d7/a0-a2/a6,-(sp)
 bsr draw_overhead_clear_spans
 bra draw_overhead_mask_begin

; Seed the native table once: its executable data initially contains zeros.
; Thereafter edge writers track the rows they touch in
; +90AA/+90AE; clear their inclusive, clipped range before the next polygon.
; Also used by E1 when no chip mask clear is necessary. Preserve registers.
draw_overhead_clear_spans:
 movem.l d0-d2/a0-a1,-(sp)
 lea draw_overhead_span_ready(pc),a0
 tst.w (a0)
 bne .bounded
 move.w #1,(a0)
 moveq #0,d1
 move.w #199,d2
 bra .range
.bounded:
 movea.l draw_overhead_h0(pc),a1
 adda.l #$90aa,a1
 move.w (a1),d1
 move.w 4(a1),d2
 tst.w d1
 bpl .top
 moveq #0,d1
.top:
 cmpi.w #199,d2
 ble .bottom
 move.w #199,d2
.bottom:
 sub.w d1,d2
 bmi .done
.range:
 movea.l draw_overhead_h0(pc),a0
 adda.l #$8d88,a0
 lsl.w #2,d1
 adda.w d1,a0
 move.l #$ffff0000,d0
.clear:
 move.l d0,(a0)+
 dbf d2,.clear
.done:
 movem.l (sp)+,d0-d2/a0-a1
 rts
 even
draw_overhead_h0: dc.l 0
draw_overhead_span_ready: dc.w 0
draw_overhead_mask_begin: ds.b 12
