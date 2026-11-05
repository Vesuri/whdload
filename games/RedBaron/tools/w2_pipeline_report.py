import json,collections
from pathlib import Path
root=Path('tmp/prof/w2-pipeline-030');reports={}
for group in ('draw','math','line','other2'):
 log=json.loads((root/f'{group}-clock.json').read_text());report=json.loads((root/f'{group}-summary.json').read_text())
 inside=False;membership={}
 for row in log['rows']:
  if row['routine']=='world3d':inside=row['kind']=='enter'
  elif row['kind']=='enter':membership[row['routine'],row['step'],row['vbl'],row['beam']]=inside
 world_steps={x['step'] for x in report['accepted'] if x['routine']=='world3d'};tot=collections.defaultdict(float);counts=collections.Counter()
 for c in log['calls']:
  a,b=c['entry'],c['return_record'];threshold=report['phase_safe_from_line'];known={x['vbl'] for x in log['vblank_phase']}
  if any(x['line']<threshold or x['hpos']<=1 or x['vbl'] not in known for x in (a,b)):continue
  fields=((b['vbl']-a['vbl'])*313*227+(b['line']-a['line'])*227+b['hpos']-a['hpos'])/(313*227)
  loc='in3d' if membership.get((c['routine'],a['step'],a['vbl'],a['beam'])) else 'outside'
  if c['routine']=='world3d':loc='total'
  if a['step'] in world_steps:tot[c['routine']+' '+loc]+=fields;counts[c['routine']+' '+loc]+=1
 result=dict(steps=sorted(world_steps),fields=dict(tot),counts=dict(counts),mean_ms_per_frame={k:v/len(world_steps)*1000/49.92041 for k,v in tot.items()},percent_of_3d={k:100*v/tot['world3d total'] for k,v in tot.items()},excluded=len(report['excluded']),phase_threshold=report['phase_safe_from_line'])
 reports[group]=result;print(group,json.dumps(result,indent=2))
(root/'breakdown.json').write_text(json.dumps(reports,indent=2)+'\n')
