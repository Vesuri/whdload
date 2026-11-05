from pathlib import Path
p=Path('src/cpu_work.s');s=p.read_text();i=s.index('f_hud_init:');tail=s[i:];tail=tail.replace(' lea f_hud_state(pc),a0',' bsr f_text_init\n lea f_hud_state(pc),a0',1);s=s[:i]+tail
s=s.replace('f_hud_reset:\n lea','f_hud_reset:\n lea f_text_cache(pc),a0\n move.w #512-1,d0\n.text:\n clr.l (a0)+\n dbf d0,.text\n lea',1)
s+='''
; Cache only the dedicated race clock/rank glyph calls. The odometer shares
; the speed needle's restore rectangle and must keep redrawing. Mirrors contain
; changing object overlays, so their unchanged backgrounds still need clearing.
f_text_init:
 move.l a5,a1
 adda.l #$880e,a1
 lea f_hud_text(pc),a0
 move.w #$4eb9,(a1)
 move.l a0,2(a1)
 move.l a5,a1
 adda.l #$8858,a1
 move.w #$4eb9,(a1)
 move.l a0,2(a1)
 lea f_text_native(pc),a0
 move.l a5,d0
 addi.l #$33740,d0
 move.l d0,2(a0)
 lea f_glyph_native(pc),a0
 move.l a5,d0
 addi.l #$349e0,d0
 move.l d0,2(a0)
 move.l a5,a1
 adda.l #$349d6,a1
 lea f_glyph(pc),a0
 move.w #$4ef9,(a1)
 move.l a0,2(a1)
 rts
f_hud_text:
 move.l a0,-(a7)
 lea f_text_active(pc),a0
 st (a0)
 move.l (a7)+,a0
 bsr f_text_native
 move.l a0,-(a7)
 lea f_text_active(pc),a0
 clr.b (a0)
 move.l (a7)+,a0
 rts
f_text_native:
 jmp $0
f_text_active: dc.w 0
f_text_cache: ds.b 2048
f_glyph:
 tst.b f_text_active(pc)
 beq .draw
 cmpi.w #8,d7
 bne .draw
 movem.l d0/d2/a0/a2,-(a7)
 move.l a3,d0
 andi.w #127,d0
 lsl.w #4,d0
 lea f_text_cache(pc),a2
 adda.w d0,a2
 cmp.l (a2),a3
 bne .update
 cmp.l 4(a2),a1
 bne .update
 cmp.w 8(a2),d4
 bne .update
 movem.l (a7)+,d0/d2/a0/a2
 move.b 7(a1),d1
 addq.l #8,a1
 move.w d4,d5
 lsr.b #4,d5
 move.l #$6270,d6
 move.w #-1,d7
 lea $150(a3),a4
 addq.l #1,a3
 rts
.update:
 move.l a3,(a2)
 move.l a1,4(a2)
 move.w d4,8(a2)
 movem.l (a7)+,d0/d2/a0/a2
.draw:
 move.l a3,a4
 subq.w #1,d7
 move.l #$6270,d6
f_glyph_native:
 jmp $0
''';p.write_text(s)
