from pathlib import Path
import json,hashlib
root=Path('tmp/prof');out={}
for window,off,on in [('A','p2-ready-a-off','p2-ready-a-on'),('B','p2-ready-b-off','p2-ready-b-on')]:
 ds=[json.loads((root/n/'frame-budget.json').read_text()) for n in [off,on]]
 assert (root/off/'slave.slave').read_bytes()==(root/on/'slave.slave').read_bytes()
 costs=[d['modules'].get('slave_record',0)+d['inclusive'].get('record',{}).get('ms_per_frame',0) for d in ds]
 rows=[]
 for name,d,cost in zip([off,on],ds,costs):
  rows.append(dict(run=name,recorder_ms=cost,camera_record_ms=d['phases']['0d960 camera+record'],swaps=d['swaps'],complete_frames=d['complete_frames'],frame_ms=d['mean_frame_ms'],polygons=sum(f['polys'] for f in d['frames'])/d['complete_frames'],fps=1000/d['mean_frame_ms']))
 out[window]=dict(off=rows[0],on=rows[1],overhead_ms=costs[1]-costs[0],limit_ms=.3,passed=costs[1]-costs[0]<=.3,scene_mismatch=abs(rows[1]['polygons']/rows[0]['polygons']-1)>.05)
(root/'p2-summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
d=json.loads((root/'p2-ready-disabled/disabled.json').read_text());print('disabled',d['passed'],len(d['ranges']))
