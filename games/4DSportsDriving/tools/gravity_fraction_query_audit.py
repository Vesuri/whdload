#!/usr/bin/env python3
"""Read-only one-step query sensitivity to pending downward displacement fraction.
Each pre-gravity and post-gravity comparison is independent, not combined into
an alternative trajectory. No claim that all fractional state can be added to
body geometry without a coherent reconstruction is made.
"""
import json
from pathlib import Path
from coupled_vehicle_core import seed,advance,summarize
from native_contact_response import plane
r=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 cap=r/('crest-d9e7903'if phase=='nominal'else'phase-'+phase+'-d9');b,read,param=seed(cap);ref={v['tick']:v for v in json.loads((cap/'bridge.json').read_text())['rows']};changes=[];counts={'pre':0,'post':0};steps=0
 while b['contact']['entry'][0]<=800:
  b,rec=advance(b,50,read,param);c=rec['contact'];t=c['entry'][0];v=summarize(b);assert v['position']+[v['pitch'],v['speed']]==[ref[t][k]for k in ('x','y','z','pitch','speed')];steps+=1
  for s in c['selected']:
   w=s['wheel'];p=[s['world_'+a]for a in 'xyz'];q=s['clearance'];assert plane(s,p)==q
   def check(stage,p,f):
    if not f:return
    counts[stage]+=1;alt=p.copy();alt[1]-=1;x,y=plane(s,p),plane(s,alt)
    if x!=y:changes.append(dict(tick=t,wheel=w,stage=stage,fraction=f,old=x,new=y,gravity_change=(x>0)!=(y>0),penetration_change=(x<0)!=(y<0)))
   check('pre',p,s['position_fraction'])
   if q>0:
    acc=21 if w<2 else 15
    down,pf=divmod(10*s['velocity']+2*s['velocity_fraction']+7*acc+s['position_fraction'],25);p[1]-=down;check('post',p,pf)
 cases.append(dict(phase=phase,exact_steps=steps,nonzero_fractions=counts,changes=changes));important=[v for v in changes if v['gravity_change']or v['penetration_change']];print(phase,counts,'querychanges',len(changes),'decisionchanges',important)
(r/'gravity-fraction-query-audit.json').write_text(json.dumps(dict(scope=__doc__,cases=cases),indent=2)+'\n')
