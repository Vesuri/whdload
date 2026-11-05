import json,statistics
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'tmp';report=[]
for cell,prefix in [('a1200-fast','wait'),('a1200-fast+nocache','wait'),('030-50','cost-window'),('040-25','cost-window'),('060-50','cost-window')]:
 p=root/f'c-approved-motion-{prefix}-{cell}/windows.json'
 if not p.exists():continue
 ev=json.loads(p.read_text())['events'];ticks=[];wait=[]
 # PAL short fields: express beam phase relative to the native line-$fa SOFT tick.
 def line(e):return e['field']*312+(e['beam']-250)%312
 for a,b in zip(ev,ev[1:]):
  if a['site']=='step_main' and b['site']=='step_completed' and b['cursor']==a['cursor']+1:
   ticks.append(line(b)-line(a))
  if a['site']=='wait_begin' and b['site']=='wait_end':wait.append(line(b)-line(a))
 assert ticks and min(ticks)>=0
 row=dict(cell=cell,samples=len(ticks),approx_step_lines=dict(min=min(ticks),median=statistics.median(ticks),max=max(ticks)),approx_step_ms=dict(min=min(ticks)*20/312,median=statistics.median(ticks)*20/312,max=max(ticks)*20/312),wait_samples=len(wait),wait_lines=wait)
 report.append(row);print(row)
(root/'c-approved-motion-step-cost.json').write_text(json.dumps(dict(scope='Read-only beam snapshots around complete simulation steps near field 300; approximate PAL 312-line conversion, line granularity, small workload sample; emulator observations, not real hardware cycle measurements.',cells=report),indent=2)+'\n')
