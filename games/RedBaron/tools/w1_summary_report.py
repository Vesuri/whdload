"""Collect completed W1 scene evidence; never talks to the emulator."""
import json
from pathlib import Path
root=Path('tmp/prof');rows=[]
for machine in ('a500','020','030'):
 for scene in ('bank','dense'):
  cases=[root/f'w1-scene-{machine}-{scene}-{mask}' for mask in (0,1,3)]
  if not all((p/'complete.json').exists() for p in cases):continue
  original=(cases[0]/'checkpoint-h3.bin').read_bytes()
  for mask,case in zip((0,1,3),cases):
   data=(case/'checkpoint-h3.bin').read_bytes();assert len(data)==len(original)==0xbd0c
   diff=[i for i,(a,b) in enumerate(zip(original,data)) if a!=b]
   log=json.loads((case/'checkpoint.json').read_text());cost=case/'window-costs.json';audit=case/'final-audit.json'
   rows.append(dict(machine=machine,scene=scene,mask=mask,differing_h3_bytes=len(diff),difference_offsets=diff,dt_values=sorted({r['dt'] for r in log['records']}),costs=json.loads(cost.read_text())['summary'] if cost.exists() else None,audit=json.loads(audit.read_text()) if audit.exists() else None))
report=dict(scene_cases=len(rows),expected_scene_cases=18,complete=len(rows)==18 and all(r['audit'] is not None for r in rows),rows=rows)
(root/'w1-scene-summary.json').write_text(json.dumps(report,indent=2)+'\n')
for r in rows:print(r['machine'],r['scene'],r['mask'],'h3',r['differing_h3_bytes'],'dt',r['dt_values'],'3D',r['costs'].get('world3d') if r['costs'] else 'DMA only')
print('complete',report['complete'])
