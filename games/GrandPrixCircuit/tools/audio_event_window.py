import sys,struct,json
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
p=Path(sys.argv[1]);target=int(sys.argv[2]);part=target//7105100;t=barto.load(p/f'intro-trace-{part:02d}.bin');rows=[]
for f in t.fields:
 for i,o in enumerate(range(0,len(f.dma),f.dma_size)):
  now=(part*100+f.index)*71051+i
  if abs(now-target)>4000:continue
  typ=f.dma[o+29];r=struct.unpack_from('<H',f.dma,o)[0];v=struct.unpack_from('<I',f.dma,o+2)[0]&65535;adr=struct.unpack_from('<I',f.dma,o+12)[0]
  if typ==2 and r==0x1102 and (0xdff096<=adr<=0xdff0de):rows.append([now-target,'write',hex(adr-0xdff000),hex(v)])
  if typ==4:rows.append([now-target,'audio',hex(r),hex(adr),hex(v)])
(p/'suspect-window.json').write_text(json.dumps(rows,indent=2)+'\n');print('\n'.join(map(str,rows)))
