#!/usr/bin/env python3
"""Summarize and validate the completed measurement matrix, without rerunning it."""
import json,sys
from pathlib import Path
import _amigaxdev
from amigaxdev import aprof
root=Path(sys.argv[1]);rows=[]
for p in sorted(root.glob('*/*/result.json')):
 r=json.loads(p.read_text());out=p.parent
 assert r['end_vbl']-r['start_vbl']==500
 assert len(r['frame_log'])==r['frames']
 assert all(a[2]^b[2]==1 for a,b in zip(r['frame_log'],r['frame_log'][1:]))
 assert all(a[0]<=b[0] for a,b in zip(r['frame_log'],r['frame_log'][1:]))
 profile=out/'window.prof'
 if profile.exists():
  _,pcs,_=aprof.parse_profile(profile.read_text());L=json.loads((out/'layout.json').read_text())
  assert pcs.get(L['gamemule']+0x44ca,(0,0))[1]==r['frames']
  r['full_shapes_per_frame']=pcs.get(L['gamemule']+0x6348,(0,0))[1]/r['frames']
 else:
  t=json.loads((out/'trace-check.json').read_text());assert 0 <= r['frames']-t['trace_swaps'] <= t.get('unrecorded_lead_in_fields',0)
 rows.append({k:r[k] for k in ('mode','machine','frames','fps','ticks_per_second','pacing')} | ({'full_shapes_per_frame':r['full_shapes_per_frame']} if profile.exists() else {}))
 print(f"{r['mode']:8} {r['machine']:12} fps {r['fps']:4.1f} ticks/s {r['ticks_per_second']:3.1f} intervals {r['pacing']['interval_histogram_fields']}")
(root/'summary.json').write_text(json.dumps(rows,indent=2))
