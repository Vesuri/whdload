from pathlib import Path
import json,hashlib
root=Path('tmp/prof');out={}
for w,limit in [('a',1.75),('b',1.25)]:
 ns=[f'p3-final-{w}-off',f'p3-final-{w}-on'];ds=[json.loads((root/n/'frame-budget.json').read_text()) for n in ns]
 assert (root/ns[0]/'slave.slave').read_bytes()==(root/ns[1]/'slave.slave').read_bytes()
 assert (root/ns[0]/'slave.lst').read_bytes()==(root/ns[1]/'slave.lst').read_bytes()
 rows=[]
 for n,d in zip(ns,ds):
  rows.append(dict(run=n,engine_entries=d['entries_per_frame']['engine'],frame_ms=d['mean_frame_ms'],fps=1000/d['mean_frame_ms'],swaps=d['swaps'],complete_frames=d['complete_frames'],polygons=sum(f['polys'] for f in d['frames'])/d['complete_frames'],physics_ms=d['phases']['0cda4 physics'],phase_helper_ms=d['modules'].get('slave_phase',0)))
 previous=json.loads((root/f'p2-ready-{w}-on'/'frame-budget.json').read_text())
 cache=json.loads((root/ns[1]/'engine-cache.json').read_text())
 out[w.upper()]=dict(off=rows[0],on=rows[1],limit=limit,passed=rows[1]['engine_entries']<=limit,cache=cache,scene_mismatch=abs(rows[1]['polygons']/rows[0]['polygons']-1)>.05,p2_engine_entries=previous['entries_per_frame']['engine'],p2_frame_ms=previous['mean_frame_ms'],p2_physics_ms=previous['phases']['0cda4 physics'])
(root/'p3-summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
