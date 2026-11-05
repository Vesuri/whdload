from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1];dst=root/'tmp/c-road-lifecycle-source';shutil.copytree(root/'tmp/c-road-actors-source',dst,dirs_exist_ok=True)
p=dst/'RoadRashHD.s';s=p.read_text().replace('PL_PS $BCD0,step_actor_road','PL_PS $BCD0,step_actor_road\n\tPL_PSS $BDF0,step_actor_road_copy,6');p.write_text(s)
p=dst/'steering.s';s=p.read_text();s=s.replace('lea step_steering_fraction(pc),a0\n\tclr.l (a0)\n\tmove.l (a7)+,a0\n.done:', 'lea step_steering_fraction(pc),a0\n\tclr.l (a0)\n\tlea step_road_fraction(pc),a0\n\tclr.l (a0)+\n\tclr.l (a0)+\n\tclr.l (a0)\n\tmove.l (a7)+,a0\n.done:',1)
s+='''
; Keep external fractional road position with native companion record copies.
step_actor_road_copy:
 movem.l d0-d2/a2,-(a7)
 move.l a0,d0
 subi.l #$a5d60,d0
 cmpi.l #$1180,d0
 bcc .done
 move.l d0,d2
 andi.l #$7f,d2
 bne .done
 lsr.l #5,d0
 lea step_actor_road_fraction(pc),a2
 adda.l d0,a2
 move.l a1,d1
 subi.l #$a5d60,d1
 cmpi.l #$1180,d1
 bcc .clear
 move.l d1,d2
 andi.l #$7f,d2
 bne .clear
 lsr.l #5,d1
 sub.l d0,d1
 move.l (a2,d1.w),(a2)
 bra .done
.clear:
 clr.l (a2)
.done:
 movem.l (a7)+,d0-d2/a2
 lsr.w $2c(a0)
 move.w #1,$8b484
 rts
''';p.write_text(s)
