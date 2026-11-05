#!/usr/bin/env python3
"""Collect >= N PAL fields of swaps and step logs without overflowing the observer ring."""
import argparse,json,subprocess,sys
from pathlib import Path
import step_log
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--fields',default=2000,type=int);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
initial=step_log.collect();rows={v['step']:v for v in initial['records']};first=initial['records'][-1];swaps=[];at=first
while at['vbl']-first['vbl']<a.fields:
    target=at['step']+200;path=a.out/f'to-{target}.json'
    subprocess.run([sys.executable,'tools/swap_fields.py','--step',str(target),'--out',str(path)],check=True)
    part=json.loads(path.read_text());swaps.extend(part['swaps'])
    for row in part['steps']['records']:
        if row['step'] in rows and rows[row['step']]!=row:raise RuntimeError('Ring record changed before wrap')
        rows[row['step']]=row
    at=part['steps']['records'][-1]
    (a.out/'progress.json').write_text(json.dumps(dict(first=first,last=at,swaps=swaps,records=sorted(rows.values(),key=lambda x:x['step'])),indent=2)+'\n')
    if at['step']-first['step']>=2000:raise RuntimeError('Window still too short at 2000 steps')
result=dict(first=first,last=at,elapsed_fields=at['vbl']-first['vbl'],swaps=swaps,records=sorted(rows.values(),key=lambda x:x['step']))
result['fps']=len(swaps)*49.92041/result['elapsed_fields']
(a.out/'window.json').write_text(json.dumps(result,indent=2)+'\n')
print({k:result[k] for k in ('elapsed_fields','fps')},'swaps',len(swaps))
