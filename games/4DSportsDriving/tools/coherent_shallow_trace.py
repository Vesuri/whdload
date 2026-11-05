#!/usr/bin/env python3
"""Record when the rejected common-contact correction alters body orientation."""
from pathlib import Path
import json
from coupled_vehicle_core import seed,advance,summarize
from coherent_shallow_support_model import solve
from contact_body_predictor import body
root=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 cap=root/('crest-d9e7903'if phase=='nominal'else'phase-'+phase+'-d9');b,read,param=seed(cap);rows=[]
 def observed(e,build,selected,state):
  result=solve(e,build,selected,state)
  if any(w['branch']=='coherent_shallow'for w in result['wheels']):
   native=body(e,build,selected)
   rows.append(dict(tick=e[0],incoming_pitch=e[2],clearances=[r['clearance']for r in selected],plane=selected[0]['plane'],baseline_same_input_pitch=native['pitch'],candidate_pitch=result['pitch'],position_difference=[x-y for x,y in zip(result['position'],native['position'])]))
  return result
 while b['contact']['entry'][0]<=800:b,_=advance(b,50,read,param,solver=observed)
 cases.append(dict(phase=phase,modified_steps=len(rows),rows=rows))
 print(phase,'eligible',len(rows),'first orientation changes',[x for x in rows if x['candidate_pitch']!=x['baseline_same_input_pitch']][:5])
(root/'coherent-shallow-trace.json').write_text(json.dumps(dict(scope=__doc__,cases=cases),indent=2)+'\n')
