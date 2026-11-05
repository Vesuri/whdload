#!/usr/bin/env python3
"""Same native20 airborne state evolved at20/50Hz through the first flight.
No reference injection after initialization; offline straight stock-car scope.
"""
from pathlib import Path
from copy import deepcopy
import json
from coupled_vehicle_core import seed,advance,summarize
root=Path('tmp/prof');reports=[]
for phase in ('nominal','minus64','plus64'):
 cap=root/('natural-crest20'if phase=='nominal'else'phase-'+phase+'-native20');b,read,param=seed(cap)
 reference={v['tick']:v for v in json.loads((cap/'bridge.json').read_text())['rows']}
 while b['contact']['entry'][0]<=232:b,_=advance(b,20,read,param)
 initial=deepcopy(b);outcomes={};contact_times={}
 for hz in (20,50):
  b=deepcopy(initial);b['contact']['entry'][0]=58*hz//5+1
  if hz==50:
   for o in (0xc6,0xcb):b['car'][o]=(5*b['car'][o]+1)//2
  rows=[];first_contact=None
  while b['contact']['entry'][0]<=13*hz:
   tick=b['contact']['entry'][0];b,rec=advance(b,hz,read,param);v=summarize(b)
   if first_contact is None and any(w['branch']!='air'for w in rec['contact']['output']['wheels']):first_contact=tick*1000//hz
   if hz==20:assert v['position']+[v['pitch'],v['speed']]==[reference[tick][k]for k in ('x','y','z','pitch','speed')]
   if tick%(hz//10)==0:rows.append(dict(time_tenths=tick*10//hz,state=v))
  outcomes[str(hz)]=rows;contact_times[str(hz)]=first_contact
 errors=[]
 for a,b in zip(outcomes['20'],outcomes['50']):
  assert a['time_tenths']==b['time_tenths'];x,y=a['state'],b['state']
  errors.append(dict(time_tenths=a['time_tenths'],position=[v-u for u,v in zip(x['position'],y['position'])],**{k:y[k]-x[k]for k in ('pitch','speed','target')}))
 limit=min(t for t in [*contact_times.values(),13001]if t is not None)
 air_errors=[v for v in errors if v['time_tenths']*100<limit]
 reports.append(dict(phase=phase,initial=summarize(initial),errors=errors,outcomes=outcomes,first_contact_ms=contact_times,last_common_airborne_error=air_errors[-1]))
report=dict(scope=__doc__,cases=reports)
(root/'coupled-matched-flight-family.json').write_text(json.dumps(report,indent=2)+'\n')
for row in reports:print(row['phase'],'first contacts',row['first_contact_ms'],'last shared airborne',row['last_common_airborne_error'],'13s',row['errors'][-1])
