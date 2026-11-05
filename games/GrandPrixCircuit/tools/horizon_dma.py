import sys,struct,json,collections
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
p=Path(sys.argv[1]);t=barto.load(p/'trace.bin');regs={};blits=[];kinds=collections.Counter();events=[]
for f in t.fields:
 for i,o in enumerate(range(0,len(f.dma),f.dma_size)):
  typ=f.dma[o+29];reg=struct.unpack_from('<H',f.dma,o)[0];addr=struct.unpack_from('<I',f.dma,o+12)[0];val=struct.unpack_from('<I',f.dma,o+2)[0]
  if typ==5:kinds[hex(reg)]+=1;events.append((f.index,i,reg,addr,val&65535))
  if typ==2 and reg in (0x1102,0x1104) and 0xdff040<=addr<=0xdff074:
   off=addr-0xdff000
   if reg==0x1104:regs[off]=val>>16;regs[off+2]=val&65535
   else:regs[off]=val&65535
   if off==0x58:
    blits.append(dict(field=f.index,index=i,registers={hex(k):v for k,v in regs.items()}))
(p/'blits.json').write_text(json.dumps(blits,indent=2)+'\n');(p/'blit-events.json').write_text(json.dumps(events)+'\n')
print('blits',len(blits),'DMA kinds',kinds)
for x in blits:
 r=x['registers']
 if r.get('0x66')==65534:print(x)
