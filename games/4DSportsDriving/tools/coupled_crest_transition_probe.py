#!/usr/bin/env python3
"""Detailed equal-state11.1..11.3s approach transition at20/50Hz."""
from pathlib import Path
from copy import deepcopy
import json
from coupled_vehicle_core import seed,advance,summarize
from native_contact_response import word
root=Path('tmp/prof');reports=[]
for phase in ('nominal','minus64','plus64'):
 cap=root/('natural-crest20'if phase=='nominal'else'phase-'+phase+'-native20');b,read,param=seed(cap)
 while b['contact']['entry'][0]<=222:b,_=advance(b,20,read,param)
 initial=deepcopy(b);rates={}
 for hz in (20,50):
  b=deepcopy(initial);b['contact']['entry'][0]=111*hz//10+1
  if hz==50:
   for o in (0xc6,0xcb):b['car'][o]=(5*b['car'][o]+1)//2
  records=[]
  while b['contact']['entry'][0]<=113*hz//10:
   tick=b['contact']['entry'][0];before=summarize(b);b,rec=advance(b,hz,read,param);c=rec['contact'];wheels=[]
   for w,(q,v)in enumerate(zip(c['selected'],c['output']['wheels'])):
    origin=[64*word(q['base_'+a]+q['node_'+a])for a in 'xyz'];normal=[q['normal_'+a]for a in 'xyz']
    fine={p:sum((q[p+'_'+a]-o)*n for a,o,n in zip('xyz',origin,normal))/8192 for p in ('old_world','world')}
    wheels.append(dict(wheel=w,plane=q['plane'],pre_clearance=q['clearance'],fine_clearance=fine,post_clearance=v['suspension_clearance'],branch=v['branch'],velocity_before=c['entry'][21+w],velocity_fifths_after=5*b['contact']['entry'][21+w]+b['contact']['entry'][25+w],down=v['down'],old_world=[q['old_world_'+a]for a in 'xyz'],new_world=[q['world_'+a]for a in 'xyz']))
   records.append(dict(tick=tick,time_ms=tick*1000//hz,before=before,after=summarize(b),wheels=wheels))
  rates[str(hz)]=records
 reports.append(dict(phase=phase,initial=summarize(initial),rates=rates))
(root/'coupled-crest-transition-probe.json').write_text(json.dumps(dict(scope=__doc__,cases=reports),indent=2)+'\n')
for r in reports:
 print(r['phase'])
 for hz,rows in r['rates'].items():
  for v in rows:
   print(hz,v['time_ms'],'pitch',v['before']['pitch'],'->',v['after']['pitch'],[{k:w[k]for k in ('wheel','plane','pre_clearance','post_clearance','branch','velocity_fifths_after')}for w in v['wheels'][::2]])
