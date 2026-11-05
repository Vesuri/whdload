from pathlib import Path
import json,sys,collections,struct
import barto_mmap as b
from harddrivin_report import contexts
for name in sys.argv[1:]:
 p=Path('tmp/prof')/name;m=json.loads((p/'metadata.json').read_text());base=m['layout']['code_base'];t=b.load(p/'trace.bin')
 entry_sp=next(r[15] for f in t.fields for pc,c,r in t.instructions(f) if pc==base+0xcda4)
 main=next((lo,hi) for lo,hi in contexts(t,t.fields) if lo<=entry_sp<hi)
 active=None;rows=[]
 for f in t.fields:
  for pc,c,r in t.instructions(f):
   if pc==0x7fffffff or not main[0]<=r[15]<main[1]:continue
   if pc==base+0xb856:
    assert active is None;active={'input':r[0],'cycles':0,'divisions':0}
   if pc==base+0xb85c and active is not None:rows.append(active);active=None
   if active is not None:
    active['cycles']+=c
    active['divisions']+=pc in [base+0x957e,base+0x9594]
 o=8+4*len(t.sections)+16
 for _ in range(3):o+=4+struct.unpack_from('<I',t.data,o)[0]
 clock,unit=struct.unpack_from('<II',t.data,o);ms=sum(x['cycles'] for x in rows)*unit/(clock*64)*1000
 report={'calls':len(rows),'total_ms':ms,'input_min':min(x['input'] for x in rows),'input_max':max(x['input'] for x in rows),'division_calls':sum(x['divisions'] for x in rows),'rows':rows,'scope':'Complete native engine B856 root calls over the entire trace, interrupts excluded; not normalized to complete swap intervals.'}
 (p/'native-root-cost.json').write_text(json.dumps(report,indent=2)+'\n');print(name,{k:v for k,v in report.items() if k!='rows'},flush=True)
