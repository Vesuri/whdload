#!/usr/bin/env python3
"""Report completion-debt recovery without hiding unfinished final batches."""
import argparse,hashlib,json
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('capture',type=Path);args=parser.parse_args();p=args.capture
c=json.loads((p/'capacity.json').read_text());rows=c['rows']
assert c['produced']==c['fields'] and c['steady_tick_continuity']
assert [x[0] for x in rows]==list(range(c['start']['field']+1,c['end']['field']+1))
assert len(rows)==c['fields']
for edge in ('start','end'):assert c[edge]['failure']==c[edge]['overflow']==0
if c['start']['opponent']:
 assert c['opponent_calls']==c['completed']
 assert all(c['start']['cars'][car]['position']!=c['end']['cars'][car]['position'] for car in ('player','opponent'))
 assert all(c[edge]['cars'][car]['crashed']==0 for edge in ('start','end') for car in ('player','opponent'))
assert hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest()==c['slave_sha256']==json.loads((p/'launch.json').read_text())['slave_sha256']
debt=[(x[0]-c['start']['field'])-x[1] for x in rows];queue=[(x[3]-x[4])&65535 for x in rows]
recovered=[0]+[i+1 for i,d in enumerate(debt) if d<=0];last=recovered[-1]
r=dict(fields=c['fields'],produced=c['produced'],completed=c['completed'],opponent_calls=c['opponent_calls'],queue_start=c['start']['queue'],queue_end=c['end']['queue'],queue_min=min(queue),queue_max=max(queue),relative_completion_debt_min=min(debt),relative_completion_debt_max=max(debt),relative_completion_debt_end=debt[-1],fields_at_or_below_start_debt=len(recovered)-1,last_recovered_field=last,trailing_unrecovered_fields=c['fields']-last,longest_between_recoveries_fields=max(b-a for a,b in zip(recovered,recovered[1:])) if len(recovered)>1 else None,scope='Debt relative to the exact initial boundary, not absolute pending work. Recovery means publications minus completions has returned to zero or below. The final unfinished episode is reported separately. Not a hardware or overload proof.')
(p/'capacity-recovery.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
