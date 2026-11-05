#!/usr/bin/env python3
import argparse,json,collections
from pathlib import Path
from phase3_decode import decode
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();out={}
for r in sorted(a.root.glob('accepted-*')):
 if not (r/'state/counts.json').exists():continue
 m=json.loads((r/'metadata.json').read_text());fs=sorted((r/'state').glob('[0-9]*.bin'));ds=[decode(f.read_bytes(),m) for f in fs];cs=json.loads((r/'state/counts.json').read_text())
 assert all(len(f.read_bytes())==0x9364 for f in fs)
 assert {d['period'] for d in ds}=={6}
 if ds[0]['opponents']:
  assert all(ds[-1][f'AI_segment_{i}']>ds[0][f'AI_segment_{i}'] and ds[-1][f'AI_speed_{i}']>0 for i in range(1,10)),r
 out[r.name]=dict(samples=len(ds),first_field=ds[0]['native_field'],last_field=ds[-1]['native_field'],steps=cs[-1][1],publications=cs[-1][2],pause_values=sorted({d['pause'] for d in ds}),go_field=next((d['native_field'] for d in ds if d['race_running']),None),first=ds[0],last=ds[-1],status_counts=dict(collections.Counter(d['status'] for d in ds)))
(a.root/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
for name,v in out.items():print(name,{k:v[k] for k in ['samples','steps','publications','go_field']},'lap ticks',v['last']['lap_ticks'],'segment',v['last']['segment'])
