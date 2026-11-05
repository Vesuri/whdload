"""Read retained trace: native physics helper calls and multiply operands."""
import json,collections,sys
from pathlib import Path
import barto_mmap as b
from harddrivin_report import contexts
for name in sys.argv[1:]:
 p=Path('tmp/prof')/name;m=json.loads((p/'metadata.json').read_text());base=m['layout']['code_base'];t=b.load(p/'trace.bin');ranges=contexts(t,t.fields)
 sp=next(r[15] for f in t.fields for pc,c,r in t.instructions(f) if pc==base+0xcda4);main=next((a,z) for a,z in ranges if a<=sp<z)
 counts=collections.Counter();inputs=collections.Counter();products=collections.Counter();phase=False;pending=False;zero_cycles=0;cycles=0
 for f in t.fields:
  for pc,c,r in t.instructions(f):
   if pc is None or pc==0x7fffffff or not main[0]<=r[15]<main[1]:continue
   off=pc-base
   if off==0x10f24:phase=True
   elif off==0x10f28:phase=False
   if not phase:continue
   if off in [0x2950,0x295e,0x29be,0x9564,0x95a6,0xbb48,0xc022,0xb662,0xb500]:counts[hex(off)]+=1
   if off==0x29c2:
    n=r[0]&65535;n=n if n<32768 else n-65536
    inputs[n]+=1;cycles+=c
    if n==0:zero_cycles+=c
    pending=True
   elif pending:
    assert off==0x29c6
    v=r[0];v=v if v<0x80000000 else v-0x100000000
    products[v]+=1;pending=False
 report=dict(scope='Main-context physics phase across all 500 fields; includes partial boundary frames. Not a replacement gate.',calls=dict(counts),multiply_count=sum(inputs.values()),zero_multiplicands=inputs[0],zero_products=products[0],zero_multiplicand_cycles=zero_cycles,multiply_cycles=cycles,common_multiplicands=inputs.most_common(20),common_products=products.most_common(20))
 (p/'native-physics-mix.json').write_text(json.dumps(report,indent=2)+'\n');print(name,json.dumps(report),flush=True)
