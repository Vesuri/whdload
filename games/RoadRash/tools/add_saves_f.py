from pathlib import Path
p=Path('src/cpu_work.s');s=p.read_text().replace(' bsr.w f_dispatch_init',' bsr.w f_saves_init\n bsr.w f_dispatch_init',1)
s+='''
; F5a: leaf helpers only. Indirect collision callbacks keep their full saves.
f_saves_init:
 move.l a5,a0
 adda.l #$a716,a0
 move.w #$fc20,2(a0) ; d0-d5/a2, predecrement mask
 move.w #$043f,$122(a0) ; restore at $8a836 + 2
 move.l a5,a0
 adda.l #$b37e,a0
 move.w #$cfd8,2(a0) ; d0-d1/d4-d7/a0-a1/a3-a4
 move.w #$1bf3,$6a(a0) ; restore at $8b3e6 + 2
 rts
''';p.write_text(s)
