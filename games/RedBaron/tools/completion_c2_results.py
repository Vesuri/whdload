import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from completion_cadence import summarize
results={}
for machine in ('a500','020','030','040','060'):
 pair=[]
 for state in ('off','on'):
  d=ROOT/f'tmp/prof/completion-c2-{machine}-{state}'
  if not (d/'opening.json').exists():break
  pair.append(dict(entry=json.loads((d/'entry.json').read_text()),cadence=summarize((d/'opening.log').read_text(),2000),timing=json.loads((d/'opening.json').read_text())['timing']['summaries']))
 if len(pair)!=2:continue
 a,b=pair;assert a['entry']['slave_sha256']==b['entry']['slave_sha256'];assert a['entry']['mask']^b['entry']['mask']==262144
 x=a['cadence']['event_free_frame_fps'];y=b['cadence']['event_free_frame_fps']
 results[machine]=dict(off=a,on=b,gain_percent=100*(y/x-1))
 print(machine,x,y,100*(y/x-1),flush=True)
(ROOT/'tmp/prof/completion-c2-results.json').write_text(json.dumps(results,indent=2)+'\n')
