from pathlib import Path
import shutil,difflib
root=Path(__file__).resolve().parents[1];base=root/'tmp/c-combined-motion-source';dst=root/'tmp/c-combined-npc-source';shutil.copytree(base,dst,dirs_exist_ok=True)
p=dst/'RoadRashHD.s';s=p.read_text();needle='\tPL_P $BABE,step_road_reference';assert needle in s;s=s.replace(needle,'\tPL_P $B916,step_actor_lateral\n'+needle,1);p.write_text(s)
p=dst/'simulation.s';s=p.read_text();needle='\tlea step_road_fraction(pc),a1';assert needle in s;s=s.replace(needle,'\tlea step_npc_lateral_fraction(pc),a1\n\tmoveq #34,d1\n.npclateralclear:\n\tclr.l (a1)+\n\tdbf d1,.npclateralclear\n'+needle,1);p.write_text(s)
p=dst/'road_timing.s';s=p.read_text();needle=' move.l (a2,d1.w),(a2)\n bra .done';assert needle in s;s=s.replace(needle,' move.l (a2,d1.w),(a2)\n adda.l #step_npc_lateral_fraction-step_actor_road_fraction,a2\n move.l (a2,d1.w),(a2)\n bra .done',1);needle='.clear:\n clr.l (a2)';assert needle in s;s=s.replace(needle,needle+'\n adda.l #step_npc_lateral_fraction-step_actor_road_fraction,a2\n clr.l (a2)',1)
helper=(root/'tmp/c-npc-lateral-source/road_timing.s').read_text().split('; Private opponent ground-steering reference/carry experiment.',1)[1]
p.write_text(s+'\n; Private opponent ground-steering reference/carry experiment.\n'+helper)
patch=''
for name in ['RoadRashHD.s','simulation.s','road_timing.s']:
 patch+=''.join(difflib.unified_diff((base/name).read_text().splitlines(True),(dst/name).read_text().splitlines(True),fromfile=name,tofile=name))
(dst/'npc-delta.patch').write_text(patch)
