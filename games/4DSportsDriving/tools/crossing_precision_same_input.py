#!/usr/bin/env python3
"""Compare coarse/fine crossing on identical inputs along exact baseline paths."""
import json,hashlib
from pathlib import Path
from unittest.mock import patch
import contact_body_predictor as model
from coupled_vehicle_core import seed,advance,summarize
from native_contact_response import resolve as native,UnsupportedContact
from crossing_precision_model import resolve as fine
root=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 cap=root/('crest-d9e7903'if phase=='nominal'else'phase-'+phase+'-d9');b,read,param=seed(cap)
 suffix=''if phase=='nominal'else'-'+phase;ref={v['tick']:v for v in json.loads((root/('coupled-course-baseline'+suffix+'.json')).read_text())['rows']};rows=[];checked=0
 def observe(old,new,geo,distance,down,velocity,flags=0):
  out=native(old,new,geo,distance,down,velocity,flags)
  if out['branch']=='crossing':
   row=dict(tick=t,distance=distance,down=down,old=old,new=new,native_projected=out['projected_distance'],native_endpoint=out['position'])
   try:
    candidate=fine(old,new,geo,distance,down,velocity,flags)
    row.update(fine_projected=candidate['projected_distance'],fine_fraction=candidate['fine_fraction'],endpoint_delta=[y-x for x,y in zip(out['position'],candidate['position'])],stored_clearance=[out['stored_clearance'],candidate['stored_clearance']])
   except UnsupportedContact as e:row['unsupported']=str(e)
   rows.append(row)
  return out
 with patch.object(model,'resolve',observe):
  while b['contact']['entry'][0]<=800:
   t=b['contact']['entry'][0];b,_=advance(b,50,read,param);v=summarize(b);assert v['position']+[v['pitch'],v['speed']]==[ref[t][k]for k in ('x','y','z','pitch','speed')];checked+=1
 cases.append(dict(phase=phase,exact_steps=checked,crossings=len(rows),changed=sum(any(v.get('endpoint_delta',[]))for v in rows),unsupported=sum('unsupported'in v for v in rows),rows=rows))
report=dict(scope=__doc__,model_sha256=hashlib.sha256(Path('tools/crossing_precision_model.py').read_bytes()).hexdigest(),cases=cases)
(root/'crossing-precision-same-input.json').write_text(json.dumps(report,indent=2)+'\n')
for c in cases:print(c['phase'],c['crossings'],c['changed'],c['unsupported'],'first',next((r for r in c['rows']if any(r.get('endpoint_delta',[]))),None))
