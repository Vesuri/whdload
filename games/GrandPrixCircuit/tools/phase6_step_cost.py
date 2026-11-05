#!/usr/bin/env python3
import argparse,json,statistics
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();m=json.loads((a.capture/'metadata.json').read_text());h=m['code_base'];t=barto.load(a.capture/'trace.bin');events=[];active=None;total=0
for f in t.fields:
 for pc,c,r in t.instructions(f):
  total+=c
  off=pc-h if pc else -1
  if off==0x772a:
   assert active is None,'reentered native VBL'
   active=dict(field=f.index,cycles=0,step=False,parts={},part='prefix',opponents=0)
  if active is None:continue
  if off==0xa09a:active['opponents']+=1
  if off==0x7754:active['step']=True;active['part']='thermal'
  if off==0xa288:active['part']='AI'
  if off==0x775a:active['part']='player'
  if off==0x775e:active['part']='post'
  if off==0x7762:active['part']='epilogue'
  active['cycles']+=c
  part=active['part'];active['parts'][part]=active['parts'].get(part,0)+c
  if off==0x7768:
   active.pop('part');events.append(active);active=None
steps=[e for e in events if e['step']];light=[e for e in events if not e['step']];assert steps
stats=lambda xs:dict(n=len(xs),min=min(xs),mean=statistics.mean(xs),max=max(xs))
cpf=total/len(t.fields)
out=dict(fields=len(t.fields),cycles_per_field=cpf,native_callbacks=len(events),step_callback=stats([e['cycles'] for e in steps]),light_callback=stats([e['cycles'] for e in light]),parts={p:stats([e['parts'].get(p,0) for e in steps]) for p in steps[0]['parts']},steps=steps,opponents_per_step=stats([e['opponents'] for e in steps]))
out['projected_percent']={str(period):100*(out['step_callback']['mean']+(period-1)*out['light_callback']['mean'])/cpf/period for period in (6,2,1)}
out['projected_max_percent']={str(period):100*(out['step_callback']['max']+(period-1)*out['light_callback']['max'])/cpf/period for period in (6,2,1)}
(a.capture/'phase6-step-cost.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='steps'},indent=2))
