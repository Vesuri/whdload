"""Main-context cost of complete face-hub iterations that emit a point/line/polygon.

The loop begins at sim:3b43a and completes at sim:3b5da. Back-face/empty
iterations are counted separately; cut iterations are discarded at each chunk.
This is the face hub's scope, not a claim about every renderer in the game.
"""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,'tools')
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('window');a=p.parse_args()
state=json.loads((a.capture/(a.window+'-before.json')).read_text());sim=state['sim']
cost=json.loads((a.capture/(a.window+'-costs.json')).read_text());low,high=cost['irq_stack'];rows=[];active=None
trace=barto.load(a.capture/a.window/'trace.bin')
for field in trace.fields:
 for pc,cycles,regs in trace.instructions(field):
  if pc==0x7fffffff or low<=regs[15]<high:continue
  off=pc-sim
  if off==0x3b43a:
   assert active is None,'Unexpected nested/missing face-loop boundary'
   active=dict(first_field=field.index,sp=regs[15],cycles=0,emit=None)
  if active is None:continue
  active['cycles']+=cycles
  if off in [0x3b594,0x3b5c8,0x3b5d4]:
   assert active['emit'] is None
   active['emit']={0x3b594:'point',0x3b5c8:'line',0x3b5d4:'polygon'}[off]
  if off==0x3b5da:
   assert regs[15]==active['sp']
   active['last_field']=field.index;rows.append(active);active=None
emitted=[r for r in rows if r['emit']]
result=dict(complete_iterations=len(rows),emitted_iterations=len(emitted),main_cycles_per_emitted_face=sum(r['cycles'] for r in emitted)/len(emitted) if emitted else None,emitted_cycles=sum(r['cycles'] for r in emitted),cut_iteration=active,iterations=rows,scope=__doc__)
(a.capture/(a.window+'-faces.json')).write_text(json.dumps(result,indent=2)+'\n');print(a.capture.name,a.window,{k:v for k,v in result.items() if k not in ['iterations','scope','cut_iteration']})
