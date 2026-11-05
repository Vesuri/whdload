"""Paired observation-schedule check for the private passive-read emulator."""
import json,os,subprocess,sys
from pathlib import Path
from matrix_a import CELLS
root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
rows=[]
for cell in [c for c in CELLS if not c.endswith('-mmu')]:
 pair=[]
 for legacy in [False,True]:
  out=root/(cell+('-legacy' if legacy else ''));out.mkdir()
  env=dict(os.environ,RR_CELL=cell,RR_LEGACY_READS=str(int(legacy)))
  with (out/'run.log').open('w') as log:
   subprocess.run([sys.executable,'tools/b_read_emulator_probe.py',str(out),'--normal'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
  pair.append(json.loads((out/'result.json').read_text()))
 a,b=pair
 row=dict(cell=cell,distance=a['distance490'],fps=a['fps'],same_distance=a['distance490']==b['distance490'],same_deltas=a['sampled_deltas']==b['sampled_deltas'],same_frames=a['rotation_frames']==b['rotation_frames'],same_hashes=all(a[k]['state_sha256']==b[k]['state_sha256'] for k in ['initial','at490','end']))
 rows.append(row);(root/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n');print(row,flush=True)
 assert all(row[k] for k in ['same_distance','same_deltas','same_frames','same_hashes']),row
