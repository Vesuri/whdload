from pathlib import Path
import json,sys,struct
import barto_mmap as bm
from harddrivin_report import contexts
for name in sys.argv[1:]:
 p=Path('tmp/prof')/name;m=json.loads((p/'metadata.json').read_text());base=m['layout']['code_base'];t=bm.load(p/'trace.bin');ranges=contexts(t,t.fields);sp=next(r[15] for f in t.fields for pc,c,r in t.instructions(f) if pc==base+0xcda4);main=next((a,b) for a,b in ranges if a<=sp<b)
 active=None;rows=[];phase='other'
 o=8+4*len(t.sections)+16
 for _ in range(3):o+=4+struct.unpack_from('<I',t.data,o)[0]
 clock,unit=struct.unpack_from('<II',t.data,o);factor=unit/(clock*64)*1000
 for f in t.fields:
  for pc,c,r in t.instructions(f):
   if pc is None or pc==0x7fffffff or not main[0]<=r[15]<main[1]:continue
   if active is not None and r[15]>active['sp']:
    active['ms']=active.pop('cycles')*factor;rows.append(active);active=None
   if pc==base+0x10f24:phase='physics'
   elif pc==base+0x10f28:phase='other'
   if pc==base+0x122be:
    assert active is None
    active={'n':r[0],'d':r[1],'sp':r[15],'phase':phase,'field':f.index,'cycles':0}
   if active is not None:active['cycles']+=c
 (p/'divider-calls.json').write_text(json.dumps({'rows':rows,'scope':'Complete divider entry/return calls, interrupts excluded; includes patched entry jump.'},indent=2)+'\n')
 print(name,len(rows),sum(v['ms'] for v in rows if v['phase']=='physics'),flush=True)
