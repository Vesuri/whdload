import sys,struct,collections,json
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
p=Path(sys.argv[1]);t=barto.load(p/'trace.bin');priority=collections.Counter();irq=collections.Counter()
for f in t.fields:
 for o in range(0,len(f.dma),f.dma_size):
  if f.dma[o+29]!=2:continue
  reg=struct.unpack_from('<H',f.dma,o)[0];addr=struct.unpack_from('<I',f.dma,o+12)[0];value=struct.unpack_from('<I',f.dma,o+2)[0]
  if addr==0xdff002 and reg in (0x1001,0x1002):priority[bool(value & (4 if reg==0x1001 else 0x400))]+=1
  if addr==0xdff01c and reg==0x1002:irq[bool(value & 0x40)]+=1
r=dict(priority_reads={str(k):v for k,v in priority.items()},blitter_irq_enable_reads={str(k):v for k,v in irq.items()})
(p/'render-flags.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
