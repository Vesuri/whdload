#!/usr/bin/env python3
"""Compare native absolute pitch to current50 on identical resolved wheel geometry."""
import json,hashlib
from pathlib import Path
from coupled_vehicle_core import seed,advance,summarize
from native_geometric_pitch_model import solve
from contact_body_predictor import body
from native_contact_response import rotate,atan_native
from airborne_pitch_predictor import axis
root=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 suffix=''if phase=='nominal'else'-'+phase;cap=root/('crest-d9e7903'if phase=='nominal'else'phase-'+phase+'-d9');b,read,param=seed(cap)
 refs=json.loads((root/('coupled-course-baseline'+suffix+'.json')).read_text())['rows'];rows=[]
 def observe(e,build,selected,state):
  original=body(e,build,selected);candidate=solve(e,build,selected,state)
  basis=[[a+d for a,d in zip(end['position'],rotate([0,384+su['returned'],0],e[4:13]))]for end,su in zip(original['wheels'],original['suspensions'])]
  raw=atan_native(*axis(basis))-256
  for key in ('wheels','suspensions','position','centroid_carries'):assert original[key]==candidate[key]
  rows.append(dict(tick=e[0],old_pitch=e[2],old_carry=e[41],current_pitch=original['pitch'],current_carry=original['pitch_carry'],native_raw_pitch=raw,native_pitch=candidate['pitch'],native_deadband_changed=raw!=candidate['pitch'],integer_difference=candidate['pitch']-original['pitch'],branches=[w['branch']for w in original['wheels']]))
  return original
 for ref in refs:
  b,rec=advance(b,50,read,param,solver=observe);v=summarize(b)
  observed=dict(tick=ref['tick'],**dict(zip(('x','y','z'),v['position'])),pitch=v['pitch'],distance=rec['engine']['distance'],**{k:v[k]for k in ('speed','target','rpm','gear','clutch','flags')},carry=b['carry'])
  assert observed==ref
 changed=[r for r in rows if r['integer_difference']]
 cases.append(dict(phase=phase,exact_reported_rows=len(refs),integer_changes=len(changed),largest_integer_difference=max(abs(r['integer_difference'])for r in rows),native_deadband_changes=sum(r['native_deadband_changed']for r in rows),first_integer_change=changed[0]if changed else None,rows=rows))
report=dict(scope=__doc__,cases=cases,model_sha256=hashlib.sha256(Path('tools/native_geometric_pitch_model.py').read_bytes()).hexdigest())
(root/'native-geometric-pitch-same-input.json').write_text(json.dumps(report,indent=2)+'\n')
for c in cases:print(json.dumps({k:v for k,v in c.items()if k!='rows'}))
