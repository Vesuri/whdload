"""Report completed same-build bit-16 pairs into the single scoreboard."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from completion_cadence import summarize
results={}
for machine in ['020','030','040','060']:
 pair=[]
 for state in ['off','on']:
  directory=ROOT/f'tmp/prof/completion-b1-{machine}-{state}'
  name='steady' if machine=='020' else 'opening'
  if not (directory/(name+'.json')).exists():break
  meta=json.loads((directory/'entry.json').read_text())
  cadence=summarize((directory/(name+'.log')).read_text(),2000)
  timing=json.loads((directory/(name+'.json')).read_text())['timing']['summaries']
  pair.append(dict(meta=meta,cadence=cadence,timing=timing))
 if len(pair)!=2:continue
 a,b=pair
 assert a['meta']['slave_sha256']==b['meta']['slave_sha256']
 assert a['meta']['mask']^b['meta']['mask']==65536
 assert a['meta']['realism_sha256']==b['meta']['realism_sha256']
 off=a['cadence']['event_free_frame_fps'];on=b['cadence']['event_free_frame_fps']
 results[machine]=dict(off=a,on=b,gain_percent=100*(on/off-1))
 print(machine,f'{off:.3f} -> {on:.3f}; {results[machine]["gain_percent"]:+.1f}%',flush=True)
(ROOT/'tmp/prof/completion-b1-results.json').write_text(json.dumps(results,indent=2)+'\n')
p=ROOT/'docs/profiling.md';lines=p.read_text().splitlines()
for i,line in enumerate(lines):
 for machine,prefix in [('020','| 020,'),('030','| 030/50, 2M chip + 8M fast, MMU |'),('040','| 040/25'),('060','| 060/50')]:
  if line.startswith(prefix) and machine in results:
   r=results[machine];a=r['off']['cadence']['event_free_frame_fps'];b=r['on']['cadence']['event_free_frame_fps'];cells=line.split('|');cells[-2]=f' {a:.3f} → {b:.3f} ({r["gain_percent"]:+.1f}%) ';lines[i]='|'.join(cells)
p.write_text('\n'.join(lines)+'\n')
