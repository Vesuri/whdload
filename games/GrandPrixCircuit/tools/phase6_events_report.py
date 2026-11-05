#!/usr/bin/env python3
import json,argparse
from pathlib import Path
from phase3_decode import decode
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args()
for root in sorted(a.root.glob('events-*')):
 if not (root/'state/metadata.json').exists():continue
 m=json.loads((root/'metadata.json').read_text());vs=[decode(f.read_bytes(),m) for f in sorted((root/'state').glob('[0-9]*.bin'))]
 event=[v for v in vs if v['native_field']>=180]
 stop=next((v for v in event if v['speed']==0),None)
 paused=[v['native_field'] for v in event if v['pause']]
 print(root.name,'stop',None if stop is None else (stop['native_field'],stop['distance_q8']/256,stop['lap_ticks']),'pause',None if not paused else (paused[0],paused[-1]),'statuses',sorted(set(v['status'] for v in vs)),'native markers',json.loads((root/'state/events.json').read_text()))
