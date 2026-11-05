from pathlib import Path
p=Path('src/cpu_work.s');s=p.read_text().replace(' bsr.w f_saves_init',' bsr.w f_hud_init\n bsr.w f_saves_init',1)
s+='''
; F3: private per-buffer needle keys. Preparation invalidates both buffers.
; Keep all native restore/draw work on a miss; never add a presentation wait.
f_hud_init:
 cmpi.l #3,verify_c_selection+20
 bne .done
 lea f_hud_state(pc),a0
 move.l a5,d0
 addi.l #$25924,d0
 move.l d0,(a0)
 lea f_speed_resume(pc),a0
 move.l a5,d0
 addi.l #$863e,d0
 move.l d0,2(a0)
 lea f_tacho_resume(pc),a0
 addi.l #$76,d0
 move.l d0,2(a0)
 move.l a5,a1
 adda.l #$8636,a1
 lea f_speed(pc),a0
 move.w #$4ef9,(a1)
 move.l a0,2(a1)
 move.l a5,a1
 adda.l #$86ac,a1
 lea f_tacho(pc),a0
 move.w #$4ef9,(a1)
 move.l a0,2(a1)
.done:
 rts
f_hud_reset:
 lea f_needle_keys(pc),a0
 moveq #7,d0
.clear:
 clr.l (a0)+
 dbf d0,.clear
 rts
f_hud_state: dc.l 0
f_needle_keys: ds.l 8 ; key/valid for speed0, speed1, tacho0, tacho1
f_speed:
 movem.l d0-d2/a0-a2,-(a7)
 lea f_needle_keys(pc),a0
 move.l f_hud_state(pc),a1
 moveq #0,d0
 move.w $44e(a1),d0
 bsr f_needle_check
 bne .draw
 movem.l (a7)+,d0-d2/a0-a2
 rts
.draw:
 movem.l (a7)+,d0-d2/a0-a2
 move.l $408.w,a3
 lea $19ce(a3),a3
f_speed_resume:
 jmp $0
f_tacho:
 movem.l d0-d2/a0-a2,-(a7)
 lea f_needle_keys+16(pc),a0
 move.l f_hud_state(pc),a1
 move.w $454(a1),d1
 add.w d1,d1
 move.w $e(a1,d1.w),d1
 ext.l d1
 swap d1
 lsr.l #8,d1
 lsr.l #6,d1
 move.w d1,$32(a1) ; preserve native current-gear scaling even on a cache hit
 move.w $44e(a1),d0
 swap d0
 move.w d1,d0
 bsr f_needle_check
 bne .draw
 movem.l (a7)+,d0-d2/a0-a2
 rts
.draw:
 movem.l (a7)+,d0-d2/a0-a2
 move.l $408.w,a3
 lea $1afc(a3),a3
f_tacho_resume:
 jmp $0
f_needle_check:
 move.l $408.w,d2
 cmpi.l #$6f780,d2
 beq .known
 addq.l #8,a0
 cmpi.l #$77cc0,d2
 bne .miss
.known:
 tst.l 4(a0)
 beq .update
 cmp.l (a0),d0
 beq .hit
.update:
 move.l d0,(a0)
 move.l #1,4(a0)
.miss:
 moveq #1,d2
 rts
.hit:
 moveq #0,d2
 rts
''';p.write_text(s)
p=Path('src/simulation.s');s=p.read_text().replace('\tbsr e_dirty_reset','\tbsr e_dirty_reset\n\tbsr f_hud_reset',1);p.write_text(s)
