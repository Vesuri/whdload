from pathlib import Path
p=Path('src/cpu_work.s');s=p.read_text();s=s.replace(' bsr.w f_geometry_init',' bsr.w f_patterns_init\n bsr.w f_geometry_init',1)
s+='''
; F1a prototype: one packed read, register-only word replication.
f_patterns_init:
 move.l a5,a1
 adda.l #$313d2,a1
 lea .inner(pc),a0
 moveq #9,d0
.inner_copy:
 move.w (a0)+,(a1)+
 dbf d0,.inner_copy
 addq.l #2,a1
 lea .outer(pc),a0
 moveq #9,d0
.outer_copy:
 move.w (a0)+,(a1)+
 dbf d0,.outer_copy
 rts
.inner:
 move.l $10(a5),d0
 bra.b .packed
.outer:
 move.l $18(a5),d0
.packed:
 move.w d0,d2
 swap d2
 move.w d0,d2
 swap d0
 move.w d0,a3
 swap d0
 move.w a3,d0
 nop
'''
# Inline separate templates: no branches inside the installed 20-byte block.
s=s[:s.index('.inner:\n move.l $10(a5),d0',s.index('f_patterns_init:'))]+'''.inner:
 move.l $10(a5),d0
 move.w d0,d2
 swap d2
 move.w d0,d2
 swap d0
 move.w d0,a3
 swap d0
 move.w a3,d0
 nop
.outer:
 move.l $18(a5),d0
 move.w d0,d2
 swap d2
 move.w d0,d2
 swap d0
 move.w d0,a3
 swap d0
 move.w a3,d0
 nop
'''
p.write_text(s)
