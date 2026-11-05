#!/usr/bin/env python3
"""Equal-state9.5s ramp acquisition at20/50Hz, without later state injection."""
from pathlib import Path
from copy import deepcopy
import json,hashlib
from coupled_vehicle_core import seed,advance,summarize
root=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 cap=root/('natural-crest20'if phase=='nominal'else'phase-'+phase+'-native20');b,read,param=seed(cap)
 ref={v['tick']:v for v in json.loads((cap/'bridge.json').read_text())['rows']}
 while b['contact']['entry'][0]<=190:
  t=b['contact']['entry'][0];b,_=advance(b,20,read,param);v=summarize(b)
  assert v['position']+[v['pitch'],v['speed']]==[ref[t][k]for k in ('x','y','z','pitch','speed')]
 initial=deepcopy(b);rates={}
 for hz in (20,50):
  b=deepcopy(initial);b['contact']['entry'][0]=19*hz//2+1
  if hz==50:
   for o in (0xc6,0xcb):b['car'][o]=(5*b['car'][o]+1)//2
  rows=[]
  while b['contact']['entry'][0]<=10*hz:
   t=b['contact']['entry'][0];b,rec=advance(b,hz,read,param);v=summarize(b);c=rec['contact']
   if hz==20:assert v['position']+[v['pitch'],v['speed']]==[ref[t][k]for k in ('x','y','z','pitch','speed')]
   rows.append(dict(time_ms=t*1000//hz,state=v,distance=rec['engine']['distance'],planes=[q['plane']for q in c['selected']],clearance=[q['clearance']for q in c['selected']],branches=[w['branch']for w in c['output']['wheels']],extensions=b['contact']['entry'][13:17],suspension_returns=[s['returned']for s in c['output']['suspensions']],pitch_carry=b['contact']['entry'][41]))
  rates[str(hz)]=rows
 twenty={v['time_ms']:v for v in rates['20']};errors=[]
 for row in rates['50']:
  if row['time_ms']not in twenty:continue
  x=twenty[row['time_ms']]['state'];y=row['state'];errors.append(dict(time_ms=row['time_ms'],position=[v-u for u,v in zip(x['position'],y['position'])],pitch=y['pitch']-x['pitch'],speed=y['speed']-x['speed']))
 cases.append(dict(phase=phase,initial=summarize(initial),rates=rates,common_errors=errors))
report=dict(scope=__doc__,cases=cases,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(root/'coupled-ramp-acquisition-probe.json').write_text(json.dumps(report,indent=2)+'\n')
for c in cases:
 print(c['phase'],'errors',c['common_errors'])
 for hz,rows in c['rates'].items():
  print(hz,[(v['time_ms'],v['state']['pitch'],v['branches'][::2],v['clearance'][::2])for v in rows if v['time_ms']<=9700])
