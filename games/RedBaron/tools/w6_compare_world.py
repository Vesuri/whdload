"""Inventory equal-tick state differences. No unknown bytes are normalized away."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tools').resolve()))
from render_mutations import Snapshot,region
from presentation_state import symbol
from pose_history import registry
p=argparse.ArgumentParser();p.add_argument('left',type=Path);p.add_argument('right',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
def load(root):
 e=json.loads((root/'entry.json').read_text());m=json.loads((root/'poses.json').read_text());i=json.loads((root/'world-initial.json').read_text())
 lines=(root/'slave.lst').read_text(encoding='latin-1').splitlines();base=e['entry']['game_anchor']-symbol(lines,'tape_game_anchor')
 return e,m,i,base,lines
le,lm,li,lb,ll=load(a.left);re,rm,ri,rb,rl=load(a.right)
assert le['slave_sha256']==re['slave_sha256']
assert lm['h3']==rm['h3'] and lb==rb,'Different allocation layout; do not normalize pointers'
h3=lm['h3'];header=lb+symbol(ll,'time_pose_header');loop=lb+symbol(ll,'time_loop_state')
def compare(l,r):
 lp=int.from_bytes(l.read(h3+0x4578,4),'big');rp=int.from_bytes(r.read(h3+0x4578,4),'big')
 out=dict(h3=region(l.read(h3,0xbd0c),r.read(h3,0xbd0c)),player_pointer_equal=lp==rp,
          player=region(l.read(lp,0x118),r.read(rp,0x118)))
 lreg=registry(l.read,h3);rreg=registry(r.read,h3)
 out['registry_equal']=lreg==rreg
 out['object_prefix_differences']=[dict(index=j,pointer=p,changes=region(l.read(p,26),r.read(p,26))) for j,p in enumerate(lreg) if p in rreg and l.read(p,26)!=r.read(p,26)]
 out['registered_objects']=len(lreg)
 return out
initial=compare(Snapshot(a.left,li['banks']),Snapshot(a.right,ri['banks']))
rows=[]
assert len(lm['frames'])==len(rm['frames'])
for lf,rf in zip(lm['frames'],rm['frames']):
 l=Snapshot(a.left,lf['banks']);r=Snapshot(a.right,rf['banks'])
 tick=int.from_bytes(l.read(header+4,4),'big');assert tick==int.from_bytes(r.read(header+4,4),'big')
 row=compare(l,r);row.update(tick=tick,left_draws=int.from_bytes(l.read(loop+36,4),'big'),right_draws=int.from_bytes(r.read(loop+36,4),'big'),lifecycle_equal=lf['lifecycle']==rf['lifecycle']);rows.append(row)
 print(tick,'draws',row['left_draws'],row['right_draws'],'h3',row['h3']['changed_bytes'],'player',row['player']['changed_bytes'],'objects',len(row['object_prefix_differences']))
result=dict(sha256=le['slave_sha256'],initial=initial,rows=rows,limitation='Diagnostic inventory: object prefixes are not complete heap state; differences are not classified or excused.')
a.out.write_text(json.dumps(result,indent=2)+'\n')
print('Initial h3/player differences',initial['h3']['changed_bytes'],initial['player']['changed_bytes'])
