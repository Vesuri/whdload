"""Separate completed-tick movement, input exposure and live-clock observations."""
import json,sys
from pathlib import Path
paths=list(map(Path,sys.argv[1:4]));data=[json.loads((p/'result.json').read_text()) for p in paths]
b,fast,nocache=data
for d in data:
 rows=d['rows']
 for prev,cur in zip(rows,rows[1:]):
  assert cur['cursor']-prev['cursor']==cur['delta']
  assert cur['position']-prev['position']==cur['displacement']
 if d['c_path']:assert all(r['delta']==1 for r in rows)
f={r['cursor']:r for r in fast['rows']};n={r['cursor']:r for r in nocache['rows']};common=sorted(f.keys()&n.keys())
assert all({k:v for k,v in f[t].items() if k!='live'}=={k:v for k,v in n[t].items() if k!='live'} for t in common)
# This straight-throttle run starts stationary. Sum only applied moving steps;
# retain the first input-bearing step to expose the native retroactive delta.
def exposures(d):
 result={};elapsed=0;started=False
 for r in d['rows']:
  if r['speed']>0:started=True
  if started:
   elapsed+=r['delta'];result[elapsed]=r
 return result
be=exposures(b);fe=exposures(fast);ne=exposures(nocache)
br=next(r for r in b['rows'] if r['cursor']==590);elapsed=next(e for e,r in be.items() if r is br)
assert fe[elapsed]['position']==ne[elapsed]['position']
initial=b['initial']['position'];assert initial==fast['initial']['position']==nocache['initial']['position']
result=dict(common_completed_ticks=len(common),completed_tick_equality=True,baseline=br,c_same_cursor=f[590],applied_fields=elapsed,c_equal_exposure=fe[elapsed],same_cursor_distance_difference_percent=100*((f[590]['position']-initial)/(br['position']-initial)-1),equal_exposure_distance_difference_percent=100*((fe[elapsed]['position']-initial)/(br['position']-initial)-1),sources=[str(p) for p in paths],scope='Completed player movement only. Equal applied input duration is explanatory; it does not replace the live-field acceptance gate or compare full actor state.')
(paths[1]/'clock-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
