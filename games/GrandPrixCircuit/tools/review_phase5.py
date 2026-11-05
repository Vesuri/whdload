#!/usr/bin/env python3
import json,hashlib,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parents[1]/'tmp/phase5';rows=[];repeat=[];hashes=set()
for model in ('a500','a1200','68030'):
 for arm in ('original','fixed','enhanced'):
  dirs=[r/f'{model}-{arm}-{n}' for n in (1,2)]
  metadata=[json.loads((p/'metadata.json').read_text()) for p in dirs]
  assert metadata[0]==metadata[1],(model,arm,'metadata')
  for p,m in zip(dirs,metadata):
   hashes.add(m['slave_sha256']);assert hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest()==m['slave_sha256']
  a,b=dirs;sa,sb=[json.loads((p/'swaps.json').read_text()) for p in dirs];assert sa==sb and len(sa)==1000
  f=next(i for i,n in enumerate(sa) if n);l=max(i for i,n in enumerate(sa) if n);n=sum(sa[f+1:l+1]);fps=50*n/(l-f)
  rows.append(dict(machine=model,arm=arm,intervals=n,fields=l-f,fps=fps))
  m=metadata[0];checks={}
  for fname in ('before.bin','code.bin'):
   x,y=(a/fname).read_bytes(),(b/fname).read_bytes()
   for label,address,size in [('code',m['code_base'],0xe544),('data',m['data_base'],0x9364)]:
    off=address-m['base'];assert x[off:off+size]==y[off:off+size],(model,arm,fname,label)
   diffs=[i for i,(u,v) in enumerate(zip(x,y)) if u!=v]
   checks[fname]={'whole_ram_equal':x==y,'different_ram_offsets':diffs,'game_code_and_allocated_data_equal':True}
  repeat.append(dict(machine=model,arm=arm,checks=checks))
assert len(hashes)==1
by={(x['machine'],x['arm']):x['fps'] for x in rows}
assert abs(by['a500','fixed']-by['a500','original'])<=.15
for m in ('a500','a1200','68030'):assert by[m,'enhanced']-by[m,'fixed']>.15,(m,by)
for model in ('a500','a1200'):
 for arm in ('fixed','enhanced'):
  p=r/f'trace-{model}-{arm}'
  b=json.loads((p/'buffer-audit.json').read_text());assert b['display_writes']==0
  q=json.loads((p/'metrics.json').read_text());assert q['native_vbl_pattern']==[1]*100
  v=json.loads((p/'visual-audit.json').read_text());assert not v['horizon_changes_without_buffer_change']
  flags=json.loads((p/'render-flags.json').read_text());expect=str(arm=='enhanced');assert set(flags['priority_reads'])=={expect};assert set(flags['blitter_irq_enable_reads'])=={str(arm!='enhanced')}
result=dict(slave_sha256=hashes.pop(),measurements=rows,repeat=repeat)
(r/'review.json').write_text(json.dumps(result,indent=2)+'\n')
for row in rows:print(row)
print('PASS: nine exact two-boot count/game-hunk repeats; A500 fix within 0.15 fps; optional gains above noise; four traces have safe buffers and correct hardware bits.')
