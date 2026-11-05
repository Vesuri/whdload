#!/usr/bin/env python3
"""Recover completion/input timestamps from post-producer field observations."""
import json
from pathlib import Path
root=Path('tmp/prof');out=[]
for name in ('sim-live040-no-entry-trace','sim-live040-entry-trace-control'):
 r=json.loads((root/name/'capacity-window.json').read_text());rows=r['field_samples']
 assert r['fields']==250 and r['start']['rate']==50 and r['every_field_published']
 candidates={r['start']['consumed']-1,r['start']['consumed']}
 # Single main-task coordinator: entered cursor is completed cursor or +1.
 for x in rows:candidates &= {x['consumed']-x['completed']-1,x['consumed']-x['completed']}
 assert len(candidates)==1,candidates
 origin=candidates.pop();epochs={x['fields']-x['write'] for x in rows};prefixes={x['imported']-x['read'] for x in rows}
 assert len(epochs)==len(prefixes)==1
 epoch=epochs.pop();prefix=prefixes.pop();done=0;completions=[]
 for x in rows:
  for ordinal in range(done+1,x['completed']+1):
   tick=origin+ordinal;field=x['fields']-1;captured=epoch+tick-prefix
   completions.append(dict(ordinal=ordinal,tick=tick,field=field,input_field=captured,input_to_completion_fields=field-captured))
  done=x['completed']
 if 'completion_samples' in r:assert completions==r['completion_samples']
 latency=[x['input_to_completion_fields'] for x in completions];assert min(latency)>=0
 debt=[x['queue']+x['imported']-(origin+x['completed']) for x in rows]
 out.append(dict(capture=name,start_completed_tick=origin,end_completed_tick=origin+done,completed=done,sample_to_completion_fields=dict(min=min(latency),max=max(latency),mean=sum(latency)/len(latency)),complete_debt=dict(min=min(debt),max=max(debt)),explicit_breakpoint_crosscheck='exact' if 'completion_samples' in r else 'not recorded'))
(root/'entry-trace-completion-latency.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
