from pathlib import Path
p=Path('src/cpu_work.s');s=p.read_text().replace('addi.l #$863e,d0','addi.l #$8666,d0').replace('addi.l #$76,d0','addi.l #$92,d0')
s=s.replace(' move.l d0,2(a0)\n move.l a5,a1\n adda.l #$8636,a1',' move.l d0,2(a0)\n lea f_needle_clear(pc),a0\n move.l a5,d0\n addi.l #$345f4,d0\n move.l d0,2(a0)\n move.l a5,a1\n adda.l #$8636,a1')
a=s.index('f_speed:\n');b=s.index('f_needle_check:\n',a)
s=s[:a]+'''f_speed:
 movem.l d0-d2/a0-a2,-(a7)
 lea f_needle_keys(pc),a0
 move.l f_hud_state(pc),a1
 move.w $44e(a1),d0
 cmpi.w #$38a4,d0
 bcs .divide
 move.w #$ff,d0
 bra .key
.divide:
 ext.l d0
 divu.w #$39,d0
.key:
 andi.l #$ffff,d0
 bsr f_needle_check
 bne .draw
 movem.l (a7)+,d0-d2/a0-a2
 rts
.draw:
 addq.l #4,a7
 movem.l (a7)+,d1-d2/a0-a2
 move.l d0,-(a7)
 move.l $408.w,a3
 lea $19ce(a3),a3
 lea $6a2.w,a1
 moveq #0,d6
 moveq #32,d3
 moveq #17,d7
 bsr f_needle_clear
 move.l (a7)+,d0
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
 move.w d1,$32(a1)
 move.w $44e(a1),d0
 ext.l d0
 swap d0
 divu.w d1,d0
 beq .key
 ext.l d0
 divu.w #$53,d0
.key:
 andi.l #$ffff,d0
 bsr f_needle_check
 bne .draw
 movem.l (a7)+,d0-d2/a0-a2
 rts
.draw:
 addq.l #4,a7
 movem.l (a7)+,d1-d2/a0-a2
 move.l d0,-(a7)
 move.l $408.w,a3
 lea $1afc(a3),a3
 lea $7b2.w,a1
 moveq #0,d6
 moveq #32,d3
 moveq #20,d7
 bsr f_needle_clear
 move.l (a7)+,d0
f_tacho_resume:
 jmp $0
f_needle_clear:
 jmp $0
''' +s[b:];p.write_text(s)
