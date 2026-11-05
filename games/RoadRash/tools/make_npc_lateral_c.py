from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1];src=root.parents[1]/'src';dst=root/'tmp/c-npc-lateral-source';shutil.copytree(src,dst,dirs_exist_ok=True)
p=dst/'RoadRashHD.s';s=p.read_text().replace('\tIFD VERIFY_C_ROAD_TIMING','\tIFD C_RUNTIME_ONLY\nVERIFY_C_ROAD_TIMING = 1\n\tENDC\n\tIFD VERIFY_C_ROAD_TIMING',1).replace('\tPL_P $BABE,step_road_reference','\tPL_P $B916,step_actor_lateral\n\tPL_P $BABE,step_road_reference',1);p.write_text(s)
p=dst/'simulation.s';s=p.read_text().replace('\tlea step_road_fraction(pc),a1','\tlea step_npc_lateral_fraction(pc),a1\n\tmoveq #34,d1\n.npclateralclear:\n\tclr.l (a1)+\n\tdbf d1,.npclateralclear\n\tlea step_road_fraction(pc),a1',1);p.write_text(s)
p=dst/'road_timing.s';s=p.read_text().replace(' move.l (a2,d1.w),(a2)\n bra .done',' move.l (a2,d1.w),(a2)\n adda.l #step_npc_lateral_fraction-step_actor_road_fraction,a2\n move.l (a2,d1.w),(a2)\n bra .done',1).replace('.clear:\n clr.l (a2)','.clear:\n clr.l (a2)\n adda.l #step_npc_lateral_fraction-step_actor_road_fraction,a2\n clr.l (a2)',1)
s+='''
; Private opponent ground-steering reference/carry experiment.
step_actor_lateral:
 move.l a1,d0
 subi.l #$a5d60,d0
 cmpi.l #$1180,d0
 bcc .native
 tst.b $6e(a1)
 bpl .native
 move.l $26(a1),d0
 lsl.l #2,d0
 lsr.l #8,d0
 move.w $8(a1),d1
 muls.w d1,d0
 asr.l #8,d0
 btst #5,$68(a1)
 beq .carry
 jsr $8e2d6
.carry:
 movem.l d1-d2/a0,-(a7)
 move.l a1,d1
 subi.l #$a5d60,d1
 lsr.l #5,d1
 lea step_npc_lateral_fraction(pc),a0
 adda.l d1,a0
 ext.l d0
 add.l (a0),d0
 move.l d0,d1
 bpl .divide
 addq.l #3,d0
.divide:
 asr.l #2,d0
 move.l d0,d2
 lsl.l #2,d2
 sub.l d2,d1
 move.l d1,(a0)
 movem.l (a7)+,d1-d2/a0
 move.w d0,$22(a1)
 add.w d0,(a1)
 rts
.native:
 move.l $26(a1),d0
 lsr.l #8,d0
 jmp step_physics_fast_code+$8b91c-$8b486(pc)
 cnop 0,4
step_npc_lateral_fraction: ds.l 35
''';p.write_text(s)
