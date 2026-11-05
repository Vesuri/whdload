#!/usr/bin/env python3
"""Exhaustive Q8-direction correction enumeration at fractional solver failures."""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import json,hashlib
from coupled_vehicle_core import seed,advance
from coupled_order_fraction_model import solve,evaluate,direction
from native_contact_response import UnsupportedContact
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
 e,build,rows,state=captured[0];old=direction(e[2],e[41]);carry=state['order_direction_carry'];d=rows[0]['distance']
 def correction(p,c):
  new=direction(p,c);return tuple((carry[i]+3*d*(old[i]-new[i]))//16777216 for i in range(3))
 possible={correction(q//256,q%256)for q in range(262144)};solutions=[];unsupported=Counter();near=[];supported=0
 for used in sorted(possible):
  try:out=evaluate(e,build,rows,state,used)
  except UnsupportedContact as exc:unsupported[str(exc)]+=1;continue
  supported+=1;requested=correction(out['pitch'],out['pitch_carry']);residual=tuple(v-u for u,v in zip(used,requested))
  if used==requested:solutions.append(dict(correction=used,pitch=out['pitch'],pitch_carry=out['pitch_carry']))
  if max(map(abs,residual))<=1:near.append(dict(correction=used,requested=requested,pitch=out['pitch'],pitch_carry=out['pitch_carry']))
 reports.append(dict(phase=phase,tick=e[0],enumerated_Q8_directions=262144,distinct_integer_corrections=len(possible),supported=supported,unsupported=dict(unsupported),solutions=solutions,near_residuals=near))
report=dict(scope=__doc__,cases=reports,model_sha256=hashlib.sha256(Path('tools/coupled_order_fraction_model.py').read_bytes()).hexdigest(),qualification='All Q8 directions enumerated, but unsupported contact responses remain unproven. No production root choice, fallback or tolerance change.')
(r/'contact-order-fraction-roots.json').write_text(json.dumps(report,indent=2)+'\n')
for c in reports:print(c['phase'],c['tick'],'corrections',c['distinct_integer_corrections'],'supported',c['supported'],'roots',c['solutions'],'nearest',c['near_residuals'])
