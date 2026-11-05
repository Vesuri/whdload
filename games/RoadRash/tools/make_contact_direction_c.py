from pathlib import Path
import shutil,difflib
root=Path(__file__).resolve().parents[1];base=root/'tmp/c-combined-npc-source';dst=root/'tmp/c-contact-direction-source';shutil.copytree(base,dst,dirs_exist_ok=True)
p=dst/'RoadRashHD.s';s=p.read_text().replace('\tPL_P $B916,step_actor_lateral','\tPL_P $EF5C,step_contact_direction\n\tPL_P $B916,step_actor_lateral',1);p.write_text(s)
p=dst/'road_timing.s';s=p.read_text()+'''
; Private test: do not exchange lateral headings while riding actors separate.
; Preserve detection, positional separation, damage and all non-riding paths.
step_contact_direction:
 move.w $22(a2),d0
 sub.w $22(a1),d0
 cmpa.l #$a6560,a1
 bcc .native
 cmpa.l #$a6560,a2
 bcc .native
 tst.b $6e(a1)
 bpl .native
 tst.b $6e(a2)
 bpl .native
 btst #1,$69(a1)
 beq .left
 tst.w d0
 ble .done
 bra .native
.left:
 tst.w d0
 bge .done
.native:
 jmp $8ef64
.done:
 rts
''';p.write_text(s)
patch=''
for name in ['RoadRashHD.s','road_timing.s']:
 patch+=''.join(difflib.unified_diff((base/name).read_text().splitlines(True),(dst/name).read_text().splitlines(True),fromfile=name,tofile=name))
(dst/'direction-delta.patch').write_text(patch)
