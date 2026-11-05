from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1];src=root.parents[1]/'src';dst=root/'tmp/c-road-reference-source';shutil.copytree(src,dst,dirs_exist_ok=True)
p=dst/'RoadRashHD.s';s=p.read_text();needle='\tIFD C_STEERING\n\tPL_P\t$B93A';assert needle in s;s=s.replace(needle,'\tIFD C_STEERING\n\tPL_P $BABE,step_road_reference\n\tPL_P\t$B93A',1);p.write_text(s)
p=dst/'simulation.s';s=p.read_text();needle='\tlea step_steering_fraction(pc),a1\n\tclr.l (a1)';assert needle in s;s=s.replace(needle,needle+'\n\tlea step_road_fraction(pc),a1\n\tclr.l (a1)',1);p.write_text(s)
p=dst/'steering.s';p.write_text(p.read_text()+'''
; Private test: evaluate curve displacement at the four-field reference,
; retaining quarter-unit output while running the simulation every field.
step_road_fraction: dc.l 0
step_road_reference:
 movem.l d0/d2/a0,-(a7)
 move.l $26(a1),d1
 lsl.l #2,d1
 lsr.l #8,d1
 move.w d6,d0
 lsl.w #2,d0
 muls.w d0,d1
 asr.l #8,d1
 muls.w #768,d1
 asr.l #8,d1
 lea step_road_fraction(pc),a0
 add.l (a0),d1
 move.l d1,d0
 bpl .positive
 neg.l d0
.positive:
 move.l d0,d2
 andi.l #3,d2
 lsr.l #2,d0
 tst.l d1
 bpl .store
 neg.l d0
 neg.l d2
.store:
 move.l d2,(a0)
 move.l d0,d1
 add.w d1,$36(a1)
 movem.l (a7)+,d0/d2/a0
 jmp $8bad2
''')
