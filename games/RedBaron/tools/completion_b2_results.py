"""Update cache feature columns from the bounded same-build comparisons."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from completion_cadence import summarize
results={}
for machine in ('020','030-nommu'):
 pair=[]
 for state in ('off','on'):
  d=ROOT/f'tmp/prof/completion-b2-{machine}-{state}'
  if not (d/'opening.json').exists():break
  entry=json.loads((d/'entry.json').read_text())
  pair.append(dict(entry=entry,cadence=summarize((d/'opening.log').read_text(),2000),timing=json.loads((d/'opening.json').read_text())['timing']['summaries']))
 if len(pair)!=2:continue
 a,b=pair
 assert a['entry']['slave_sha256']==b['entry']['slave_sha256']
 assert a['entry']['mask']^b['entry']['mask']==131072
 assert a['entry']['realism_sha256']==b['entry']['realism_sha256']
 x=a['cadence']['event_free_frame_fps'];y=b['cadence']['event_free_frame_fps']
 results[machine]=dict(off=a,on=b,gain_percent=100*(y/x-1))
 print(machine, x,y,100*(y/x-1),flush=True)
(ROOT/'tmp/prof/completion-b2-results.json').write_text(json.dumps(results,indent=2)+'\n')
