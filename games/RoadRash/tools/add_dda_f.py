from pathlib import Path
p=Path('src/cpu_work.s');s=p.read_text();s=s.replace(' lea f_span_sites(pc),a2',' bsr f_dda_init\n lea f_span_sites(pc),a2',1)
s+='''
; F2b prototype: Duff entry preserves the native 16.16 accumulation order.
f_dda_init:
 move.l a5,a1
 adda.l #$9b10,a1
 lea f_dda(pc),a0
 move.w #$4ef9,(a1)
 move.l a0,2(a1)
 rts
f_dda:
 move.l d0,-(a7)
 move.w d7,d0
 andi.w #7,d0
 lsl.w #3,d0
 lsr.w #3,d7
 lea .last(pc),a1
 suba.w d0,a1
 jmp (a1)
.loop:
 rept 7
 swap d1
 move.w d1,(a0)+
 swap d1
 add.l d3,d1
 endr
.last:
 swap d1
 move.w d1,(a0)+
 swap d1
 add.l d3,d1
 dbf d7,.loop
 move.l (a7)+,d0
 rts
''';p.write_text(s)
