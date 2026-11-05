"""Check the real audio IRQ path and report periods in a retained intro trace."""
import sys,struct,json,collections
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
p=Path(sys.argv[1]);h=int(sys.argv[2],0);t=barto.load(p/'intro-trace.bin');active=None;acks=skips=0;periods=collections.Counter();dma=collections.Counter()
for f in t.fields:
 for off in range(0,len(f.dma),f.dma_size):
  reg=struct.unpack_from('<H',f.dma,off)[0];val=struct.unpack_from('<I',f.dma,off+2)[0]&65535
  if f.dma[off+29]==2 and reg==0x1102:
   reg=struct.unpack_from('<I',f.dma,off+12)[0]-0xdff000
   if reg in (0xa6,0xb6,0xc6,0xd6):periods[val]+=1
   if reg==0x96:dma[hex(val)]+=1
 for pc,c,r in t.instructions(f):
  if pc==h+0x8c6:active=bool(r[0]&(1<<(r[1]&31)))
  if pc==h+0x926:
   assert active is True,'acknowledged a channel absent from the entry snapshot'
   acks+=1
  if pc==h+0x92c and active is not None:
   skips+=not active;active=None
assert acks and skips
result=dict(serviced_acknowledgements=acks,unsampled_channels_returned_without_ack=skips,audio_period_writes=dict(sorted(periods.items())),dmacon_writes=dict(dma),scope='Captured intro only; hardware audio confirmation pending.')
(p/'music-trace.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
