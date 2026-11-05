import json,sys
from pathlib import Path
sys.path.insert(0,'tools')
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
import transform_model as model
root=Path('tmp/prof/w2-g1-a500-0-r2');sim=json.loads((root/'entry.json').read_text())['entry']['sim'];rows=[]
# For type-2 calls, infer each signed vector component from an observed nonzero
# multiplier/product pair. A column with all-zero multipliers is immaterial.
pre={0x3b078:(0,0,0),0x3b080:(0,1,1),0x3b08a:(0,2,1),0x3b0a2:(1,0,0),0x3b0aa:(1,1,1),0x3b0b4:(1,2,1),0x3b0cc:(2,0,0),0x3b0d4:(2,1,1),0x3b0de:(2,2,1)}
post={0x3b07c:0x3b078,0x3b084:0x3b080,0x3b08e:0x3b08a,0x3b0a6:0x3b0a2,0x3b0ae:0x3b0aa,0x3b0b8:0x3b0b4,0x3b0d0:0x3b0cc,0x3b0d8:0x3b0d4,0x3b0e2:0x3b0de}
for name in ('steady-0','steady-1','bank'):
 active=None;t=barto.load(root/name/'trace.bin')
 for field in t.fields:
  for pc,cycles,regs in t.instructions(field):
   off=pc-sim
   if off==0x3afbe:active=dict(v=[None]*3,m=[None]*9,output=[],sp=regs[15])
   elif active:
    if off==0x3afd0:active['kind']=regs[0]&255
    if active.get('kind',0)<2:continue
    if off in pre:
     row,col,reg=pre[off];active['m'][row+3*col]=regs[reg]&65535
    if off in post:
     row,col,reg=pre[post[off]];m=model.signed(active['m'][row+3*col],16);prod=model.signed(regs[reg])
     if m:
      assert prod%m==0;v=prod//m;assert -32768<=v<=32767
      if active['v'][col] is not None:assert active['v'][col]==v
      active['v'][col]=v
     else:assert prod==0
    if off==0x3b098:active['scale']=(14-regs[1])&65535
    if off in (0x3b09a,0x3b0c4,0x3b0ee):active['output'].append(regs[0])
    if off==0x3b0f4:
     assert active.pop('sp')==regs[15] and len(active['output'])==3 and None not in active['m']
     active['zero_matrix_columns']=[i for i,x in enumerate(active['v']) if x is None];active['v']=[0 if x is None else x&65535 for x in active['v']]
     assert model.original(active['v'],active['m'],active['kind'],active['scale'])==active['output']
     rows.append(active);active=None
out=Path('tmp/plan/geometry/transform-calls.json');out.write_text(json.dumps(rows)+'\n');print(len(rows),'complete original type-2 transforms extracted')
