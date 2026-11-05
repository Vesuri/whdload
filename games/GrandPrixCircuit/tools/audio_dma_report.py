import sys,json,struct,collections
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
p=Path(sys.argv[1]);t=barto.load(p/'intro-trace.bin');types=collections.Counter();regs=collections.Counter();periods=collections.Counter();events=[];instructions=0
for f in t.fields:
 instructions+=(f.insn_end-f.insn_off)//4
 for i,o in enumerate(range(0,len(f.dma),f.dma_size)):
  typ=f.dma[o+29];types[typ]+=1
  reg=struct.unpack_from('<H',f.dma,o)[0]
  if typ==2 and reg==0x1102:
   adr=struct.unpack_from('<I',f.dma,o+12)[0];val=struct.unpack_from('<I',f.dma,o+2)[0]&65535
   if 0xdff0a0<=adr<0xdff0e0 or adr in (0xdff096,0xdff09c,0xdff09a):
    events.append([f.index,i,adr-0xdff000,val]);regs[hex(adr-0xdff000)]+=1
    if adr in (0xdff0a6,0xdff0b6,0xdff0c6,0xdff0d6):periods[val]+=1
summary=dict(fields=len(t.fields),instruction_words=instructions,dma_types=dict(types),register_writes=dict(regs),period_writes=dict(sorted(periods.items())),scope='DMA/register observations; no audible acceptance claim')
(p/'audio-dma-summary.json').write_text(json.dumps(summary,indent=2)+'\n');(p/'audio-register-events.json').write_text(json.dumps(events)+'\n');print(json.dumps(summary,indent=2))
