#!/usr/bin/env python3
"""Screen implicit contact/movement ordering with exact unmodified controls."""
from pathlib import Path
from copy import deepcopy
import json,hashlib
from coupled_vehicle_core import seed,advance,summarize
from coupled_order_contact_model import solve,control
from native_contact_response import UnsupportedContact
r=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 cap=r/('crest-d9e7903'if phase=='nominal'else'phase-'+phase+'-d9');initial,read,param=seed(cap);suffix=''if phase=='nominal'else'-'+phase
 ref=json.loads((r/('coupled-course-baseline'+suffix+'.json')).read_text())['rows'];results={}
 for name,solver in [('control',control),('candidate',solve)]:
  b=deepcopy(initial);rows=[];failure=None
  try:
   for expected in ref:
    t=b['contact']['entry'][0];b,rec=advance(b,50,read,param,solver=solver);s=summarize(b)
    if name=='control':assert s['position']+[s['pitch'],s['speed']]==[expected[k]for k in ('x','y','z','pitch','speed')]
    rows.append(dict(tick=t,state=s,iterations=b['contact']['order_iterations']))
  except UnsupportedContact as exc:failure=dict(tick=t,error=str(exc))
  results[name]=dict(steps=len(rows),failure=failure,rows=rows)
 cases.append(dict(phase=phase,results=results))
report=dict(scope=__doc__,cases=cases,model_sha256=hashlib.sha256(Path('tools/coupled_order_contact_model.py').read_bytes()).hexdigest(),decision='rejected if any nonconvergence; otherwise requires frozen-gate audit')
(r/'coupled-order-contact-screen.json').write_text(json.dumps(report,indent=2)+'\n')
for c in cases:
 print(c['phase'],[(k,v['steps'],v['failure'])for k,v in c['results'].items()])
