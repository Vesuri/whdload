from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1];src=root.parents[1]/'src';dst=root/'tmp/c-reference-motion-source';shutil.copytree(src,dst,dirs_exist_ok=True)
s='''; Private reference-integration test: preserve four-field endpoint convention.
; For constant acceleration, four unit updates sum to the native delta-4 step:
; sum(v_i + (3/2)*(v_i-v_previous)) = 4*(v_initial+4*a).
; Difference of floor(3*v/2) keeps half units without persistent actor carries.
 IFNE STEP_FIELDS-1
 FAIL "Reference motion requires one-field simulation"
 ENDC
 IFND C_PHYSICS_FAST
 FAIL "Reference motion return targets require the physics code copy"
 ENDC
reference_old_speed: dc.w 0
reference_motion_begin:
 move.l a0,-(a7)
 lea reference_old_speed(pc),a0
 move.w $12(a1),(a0)
 move.l (a7)+,a0
 move.w $14(a1),d1
 beq reference_motion_displacement
 jmp step_physics_fast_code+$8b4aa-$8b486(pc)
reference_motion_displacement:
 move.w $12(a1),d0
 move.w $a6f00,d2
 mulu.w d2,d0
 movem.l d1/d3,-(a7)
 moveq #0,d1
 move.w $12(a1),d1
 move.l d1,d3
 add.l d1,d1
 add.l d3,d1
 lsr.l #1,d1
 add.l d1,d0
 moveq #0,d1
 move.w reference_old_speed(pc),d1
 move.l d1,d3
 add.l d1,d1
 add.l d3,d1
 lsr.l #1,d1
 sub.l d1,d0
 bpl .store
 moveq #0,d0
.store:
 movem.l (a7)+,d1/d3
 move.l d0,$26(a1)
 jmp step_physics_fast_code+$8b4e2-$8b486(pc)
'''
(dst/'reference_motion.s').write_text(s)
p=dst/'RoadRashHD.s';s=p.read_text().replace('\tIFD C_STEERING\n\tPL_P\t$B93A', '\tIFD REFERENCE_MOTION\n\tPL_P $B4A4,reference_motion_begin\n\tPL_P $B4D2,reference_motion_displacement\n\tENDC\n\tIFD C_STEERING\n\tPL_P\t$B93A',1);p.write_text(s)
p=dst/'simulation.s';p.write_text(p.read_text()+'\n\tIFD REFERENCE_MOTION\n\tinclude reference_motion.s\n\tENDC\n')
