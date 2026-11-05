from pathlib import Path
p=Path('src')
s='''; F1c: merge each pair of unrolled plane fills, keeping native clipping.
; Called only after CUSTOM2/public placement validation, before cache flush.
; Rewrite relocated jump tables after their HUNK fixups. No per-frame patches.
f_cpu_init:
 IFD VERIFY_F_CONTROL
 rts
 ENDC
 lea f_span_sites(pc),a2
 moveq #2,d7
.loop:
 move.l a5,a0
 adda.l (a2)+,a0 ; first table
 move.l a5,a1
 adda.l (a2)+,a1 ; old first-plane fill area
 move.l a5,a3
 adda.l (a2)+,a3 ; native continuation
 move.l a1,d2
 move.l a1,d3
 addi.l #44,d3 ; even-length ladder follows odd-length ladder
 moveq #9,d0
.table:
 move.l d2,d1
 addi.l #36,d1
 move.l d1,(a0)+
 move.l d3,d1
 addi.l #36,d1
 move.l d1,(a0)+
 subq.l #4,d2
 subq.l #4,d3
 dbf d0,.table
 moveq #8,d0
.odd:
 move.l #$2d022100,(a1)+ ; move.l d2,-(a6) / move.l d0,-(a0)
 dbf d0,.odd
 move.l #$3d023100,(a1)+ ; final word in each plane
 bsr .branch
 moveq #9,d0
.even:
 move.l #$2d022100,(a1)+
 dbf d0,.even
 bsr .branch
 dbf d7,.loop
 rts
.branch:
 move.w #$6000,(a1)+
 move.l a3,d1
 sub.l a1,d1
 move.w d1,(a1)+
 rts
f_span_sites:
 dc.l $311a8,$311f8,$312a6
 dc.l $3140a,$3145a,$31508
 dc.l $3157e,$315ce,$3167c
'''
(p/'cpu_work.s').write_text(s)
f=p/'public_main.s';s=f.read_text().replace('.publish:\n bsr e_blitter_init','.publish:\n bsr f_cpu_init\n bsr e_blitter_init');f.write_text(s)
f=p/'RoadRashHD.s';s=f.read_text().replace('include public_main.s','include public_main.s\n\tinclude cpu_work.s');f.write_text(s)
