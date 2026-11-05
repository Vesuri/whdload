#!/usr/bin/env python3
"""Enumerate integer direction-table fixed points at failed implicit steps."""
from pathlib import Path
from copy import deepcopy
import json
from coupled_vehicle_core import seed,advance
from coupled_order_contact_model import solve,evaluate
from native_contact_response import sine,UnsupportedContact
r=Path('tmp/prof');reports=[]
for phase in ('nominal','minus64','plus64'):
 b,read,param=seed(r/('crest-d9e7903'if phase=='nominal'else'phase-'+phase+'-d9'));captured=[]
 def solver(e,build,rows,state):
  try:return solve(e,build,rows,state)
  except UnsupportedContact:
   captured.append(deepcopy((e,build,rows,state)));raise
 try:
  while b['contact']['entry'][0]<=800:b,_=advance(b,50,read,param,solver=solver)
 except UnsupportedContact:pass
 assert len(captured)==1
 e,build,rows,state=captured[0];old=[0,sine(e[2]),sine(e[2]+256)];carry=state['order_direction_carry'];d=rows[0]['distance'];solutions=[];unsupported=[];local=[]
 def correction(p):
  new=[0,sine(p),sine(p+256)];return tuple((carry[i]+3*d*(old[i]-new[i]))//65536 for i in range(3))
 for p in range(-768,256):
  used=correction(p)
  try:out=evaluate(e,build,rows,state,used)
  except UnsupportedContact as exc:unsupported.append(dict(pitch=p,error=str(exc)));continue
  residual=tuple(v-u for u,v in zip(used,correction(out['pitch'])))
  if residual==(0,0,0):solutions.append(dict(pitch_guess=p,returned_pitch=out['pitch'],correction=used))
  if abs(p-e[2])<=4:local.append(dict(pitch_guess=p,returned_pitch=out['pitch'],correction=used,residual=residual))
 reports.append(dict(phase=phase,tick=e[0],old_pitch=e[2],evaluated_directions=1024-len(unsupported),unsupported=unsupported,solutions=solutions,local=local))
report=dict(scope=__doc__,cases=reports,qualification='Only supported straight-course terrain/response domain. Unsupported trial directions remain explicitly unproven; no production fallback, clamping or root selection.')
(r/'contact-order-fixed-point-check.json').write_text(json.dumps(report,indent=2)+'\n')
for c in reports:print(c['phase'],c['tick'],'supported',c['evaluated_directions'],'solutions',c['solutions'],'nearby',c['local'])
