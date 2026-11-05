from pathlib import Path
import shutil,difflib
root=Path(__file__).resolve().parents[1];base=root/'tmp/c-combined-npc-source';dst=root/'tmp/c-npc-lifecycle-source'
shutil.copytree(base,dst,dirs_exist_ok=True)
p=dst/'RoadRashHD.s';s=p.read_text().replace('\tPL_P $B916,step_actor_lateral','\tPL_P $10C64,step_actor_reactivate\n\tPL_PS $B664,step_actor_inactive\n\tPL_P $B916,step_actor_lateral',1);p.write_text(s)
p=dst/'road_timing.s';s=p.read_text().replace(' tst.b $6e(a1)\n bpl .native',' tst.b $6e(a1)\n bmi .riding\n bsr step_npc_clear_fraction\n bra .native\n.riding:',1)
s+='''
; Discrete native repositioning starts a new fractional trajectory.
step_actor_reactivate:
 bsr step_actor_clear_fractions
 lea $a851a,a4
 jmp $90c6a

; Native off-screen movement discards the detailed riding trajectory.
step_actor_inactive:
 bsr step_npc_clear_fraction
 move.b #$ff,$6e(a1)
 rts

step_actor_clear_fractions:
 bsr step_npc_clear_fraction
 move.w sr,-(a7)
 movem.l d0-d1/a0,-(a7)
 move.l a1,d0
 subi.l #$a5d60,d0
 cmpi.l #$1180,d0
 bcc .done
 move.l d0,d1
 andi.l #$7f,d1
 bne .done
 lsr.l #5,d0
 lea step_actor_road_fraction(pc),a0
 clr.l (a0,d0.w)
.done:
 movem.l (a7)+,d0-d1/a0
 move.w (a7)+,ccr
 rts

step_npc_clear_fraction:
 move.w sr,-(a7)
 movem.l d0-d1/a0,-(a7)
 move.l a1,d0
 subi.l #$a5d60,d0
 cmpi.l #$1180,d0
 bcc .done
 move.l d0,d1
 andi.l #$7f,d1
 bne .done
 lsr.l #5,d0
 lea step_npc_lateral_fraction(pc),a0
 clr.l (a0,d0.w)
.done:
 movem.l (a7)+,d0-d1/a0
 move.w (a7)+,ccr
 rts
''';p.write_text(s)
patch=''
for name in ['RoadRashHD.s','road_timing.s']:
 patch+=''.join(difflib.unified_diff((base/name).read_text().splitlines(True),(dst/name).read_text().splitlines(True),fromfile=name,tofile=name))
(dst/'lifecycle-delta.patch').write_text(patch)
