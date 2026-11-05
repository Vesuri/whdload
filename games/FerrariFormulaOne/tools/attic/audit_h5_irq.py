from pathlib import Path
import sys,json,struct,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path(sys.argv[1]);trace=barto.load(p/'detail.bin');fields=[];writes=collections.Counter();enabled=[]
for f in trace.fields:
 # save_custom writes chipset_mask (BE32), then register-indexed BE16 words.
 state=struct.unpack_from('>H',f.custom,4+0x9a)[0];assert state==struct.unpack_from('>H',f.custom,4+0x1c)[0]
 initial=state;count=0
 if state&64:enabled.append((f.index,'start',hex(state)))
 for at in range(0,len(f.dma),f.dma_size):
  reg=struct.unpack_from('<H',f.dma,at)[0];dat=struct.unpack_from('<Q',f.dma,at+2)[0];address=struct.unpack_from('<I',f.dma,at+12)[0]
  events=[]
  if reg==0x9a or (reg&0xff00)==0x1100 and address==0xdff09a:events.append(dat&65535)
  cr,cd,ca=struct.unpack_from('<HHH',f.dma,at+36)
  if cr==0x9a or (cr&0xff00)==0x1100 and ca==0xf09a:events.append(cd)
  for value in events:
   state=(state|(value&0x7fff)) if value&0x8000 else (state&~value)
   writes[hex(value)]+=1;count+=1
   if state&64:enabled.append((f.index,at//f.dma_size,hex(state)))
 fields.append(dict(field=f.index,start_intena=hex(initial),end_intena=hex(state),writes=count))
assert not enabled,enabled
out=dict(status='passed',fields=fields,intena_writes=dict(writes),blit_enabled_observations=enabled,conclusion='BLIT enable bit0x40 is clear at every field start and throughout all recorded INTENA writes (CPU and copper, including conflict records). The remaining IRQ budget is not empty-queue BLIT service; C4-style disabling is already satisfied, so no ownership port is needed.',layout_source='Observer custom.cpp save_custom:4-byte BE chipset header, register-indexed BE16 fields; debug.h packed dma_rec offsets and CPU0x1100 write records, plus copper register writes/conflicts.')
(p/'irq-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(p.name,'BLIT always disabled',dict(writes))
